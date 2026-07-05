from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class AuthError(Exception):
    pass


class OTPRequired(AuthError):
    pass


def normalize_phone(raw: str) -> str:
    """ArenaTop API expects 12 digits without '+', e.g. 998917079732."""
    digits = re.sub(r"\D", "", raw.strip())
    if not digits:
        raise AuthError("Telefon raqami noto'g'ri")

    if digits.startswith("998") and len(digits) == 12:
        return digits

    if len(digits) == 9:
        return f"998{digits}"

    if digits.startswith("998") and len(digits) > 12:
        return digits[:12]

    raise AuthError("Telefon raqami noto'g'ri formatda")


def format_phone_display(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 12 and digits.startswith("998"):
        local = digits[3:]
        return f"+998 {local[:2]} {local[2:5]} {local[5:7]} {local[7:]}"
    return phone


@dataclass
class AuthSession:
    access_token: str
    refresh_token: str | None = None
    phone_number: str | None = None
    saved_at: str | None = None


class AuthService:
    VERIFY_ENDPOINT = "/auth/login/otp"
    REFRESH_ENDPOINT = "/auth/refresh"

    def __init__(
        self,
        base_url: str,
        phone_number: str,
        storage_path: str,
        static_token: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._phone_number = normalize_phone(phone_number)
        self._storage_path = Path(storage_path)
        self._static_token = static_token.strip() if static_token else None
        self._session: AuthSession | None = None
        self._awaiting_otp = False
        self._load()

    @property
    def phone_number(self) -> str:
        return self._phone_number

    @property
    def awaiting_otp(self) -> bool:
        return self._awaiting_otp

    def get_access_token(self) -> str | None:
        if self._static_token:
            return self._static_token
        if self._session:
            return self._session.access_token
        return None

    def _load(self) -> None:
        if self._static_token:
            return
        if not self._storage_path.exists():
            return
        try:
            raw = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        token = raw.get("access_token") or raw.get("token")
        if not token:
            return
        self._session = AuthSession(
            access_token=str(token),
            refresh_token=raw.get("refresh_token"),
            phone_number=raw.get("phone_number"),
            saved_at=raw.get("saved_at"),
        )

    def _save(self, access_token: str, refresh_token: str | None = None) -> None:
        payload = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "phone_number": self._phone_number,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._session = AuthSession(
            access_token=access_token,
            refresh_token=refresh_token,
            phone_number=self._phone_number,
            saved_at=payload["saved_at"],
        )

    @staticmethod
    def _extract_token(payload: Any) -> tuple[str | None, str | None]:
        if not isinstance(payload, dict):
            return None, None

        access = (
            payload.get("access_token")
            or payload.get("token")
            or payload.get("accessToken")
        )
        refresh = payload.get("refresh_token") or payload.get("refreshToken")

        for key in ("data", "result", "auth"):
            nested = payload.get(key)
            if isinstance(nested, dict):
                nested_access = (
                    nested.get("access_token")
                    or nested.get("token")
                    or nested.get("accessToken")
                )
                nested_refresh = nested.get("refresh_token") or nested.get(
                    "refreshToken"
                )
                access = access or nested_access
                refresh = refresh or nested_refresh

        if access is None:
            return None, refresh
        return str(access), str(refresh) if refresh else None

    async def _post_json(self, path: str, body: dict[str, Any]) -> Any:
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json=body,
                headers={"Accept": "application/json"},
            )

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise AuthError(f"API xatolik ({response.status_code}): {detail}")

        if not response.content:
            return {}
        return response.json()

    async def validate_token(self, token: str | None = None) -> bool:
        access_token = token or self.get_access_token()
        if not access_token:
            return False

        url = f"{self._base_url}/users/me"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
        return response.status_code == 200

    async def send_otp(self) -> str:
        payload = await self._post_json(
            "/auth/send-otp",
            {"phone_number": self._phone_number},
        )
        self._awaiting_otp = True

        message = payload.get("message") if isinstance(payload, dict) else None
        if message:
            return str(message)
        return f"SMS kod {format_phone_display(self._phone_number)} raqamiga yuborildi."

    async def verify_otp(self, code: str) -> None:
        code = code.strip()
        if not re.fullmatch(r"\d{4,6}", code):
            raise AuthError("Kod 4-6 ta raqamdan iborat bo'lishi kerak")

        payload = await self._post_json(
            self.VERIFY_ENDPOINT,
            {"phone_number": self._phone_number, "otp_code": code},
        )

        access_token, refresh_token = self._extract_token(payload)
        if not access_token:
            raise AuthError("OTP tasdiqlanmadi: token qaytmadi")

        self._save(access_token, refresh_token)
        self._awaiting_otp = False

    async def refresh_access_token(self) -> bool:
        if not self._session or not self._session.refresh_token:
            return False

        try:
            payload = await self._post_json(
                self.REFRESH_ENDPOINT,
                {"refresh_token": self._session.refresh_token},
            )
        except AuthError as exc:
            logger.warning("Token refresh failed: %s", exc)
            return False

        access_token, refresh_token = self._extract_token(payload)
        if access_token:
            self._save(access_token, refresh_token or self._session.refresh_token)
            return True
        return False

    async def ensure_access_token(self) -> str:
        token = self.get_access_token()
        if token and await self.validate_token(token):
            return token

        if await self.refresh_access_token():
            token = self.get_access_token()
            if token and await self.validate_token(token):
                return token

        raise OTPRequired("API token kerak. OTP kodni kiriting.")

    async def invalidate(self) -> None:
        self._session = None
        self._awaiting_otp = False
        if self._storage_path.exists():
            self._storage_path.unlink(missing_ok=True)
