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


def looks_like_phone(raw: str) -> bool:
    digits = re.sub(r"\D", "", raw.strip())
    return len(digits) in (9, 12) or (digits.startswith("998") and len(digits) >= 9)


@dataclass
class AuthSession:
    access_token: str
    refresh_token: str | None = None
    phone_number: str | None = None
    telegram_id: int | None = None
    saved_at: str | None = None


class AuthService:
    """Per-Telegram-user ArenaTop sessions with interactive phone OTP login."""

    VERIFY_ENDPOINT = "/auth/login/otp"
    REFRESH_ENDPOINT = "/auth/refresh"

    def __init__(
        self,
        base_url: str,
        storage_path: str,
        static_token: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._storage_path = Path(storage_path)
        self._static_token = static_token.strip() if static_token else None
        # telegram_id -> AuthSession
        self._sessions: dict[str, AuthSession] = {}
        self._load()

    def _key(self, telegram_id: int) -> str:
        return str(telegram_id)

    def is_logged_in(self, telegram_id: int) -> bool:
        if self._static_token:
            return True
        return self._key(telegram_id) in self._sessions

    def get_session(self, telegram_id: int) -> AuthSession | None:
        return self._sessions.get(self._key(telegram_id))

    def logged_in_telegram_ids(self) -> list[int]:
        return [int(key) for key in self._sessions.keys()]

    def get_access_token(self, telegram_id: int | None = None) -> str | None:
        if self._static_token:
            return self._static_token
        if telegram_id is not None:
            session = self.get_session(telegram_id)
            return session.access_token if session else None
        # Background jobs: any available session
        for session in self._sessions.values():
            return session.access_token
        return None

    def phone_for(self, telegram_id: int) -> str | None:
        session = self.get_session(telegram_id)
        return session.phone_number if session else None

    def _load(self) -> None:
        if self._static_token or not self._storage_path.exists():
            return
        try:
            raw = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        # New format: {"sessions": {"123": {...}}}
        sessions = raw.get("sessions")
        if isinstance(sessions, dict):
            for key, item in sessions.items():
                if not isinstance(item, dict):
                    continue
                token = item.get("access_token") or item.get("token")
                if not token:
                    continue
                self._sessions[str(key)] = AuthSession(
                    access_token=str(token),
                    refresh_token=item.get("refresh_token"),
                    phone_number=item.get("phone_number"),
                    telegram_id=int(key) if str(key).isdigit() else None,
                    saved_at=item.get("saved_at"),
                )
            return

        # Legacy single-session format
        token = raw.get("access_token") or raw.get("token")
        if token:
            telegram_id = raw.get("telegram_id")
            key = str(telegram_id) if telegram_id else "legacy"
            self._sessions[key] = AuthSession(
                access_token=str(token),
                refresh_token=raw.get("refresh_token"),
                phone_number=raw.get("phone_number"),
                telegram_id=int(telegram_id) if telegram_id else None,
                saved_at=raw.get("saved_at"),
            )

    def _save(self) -> None:
        payload = {
            "sessions": {
                key: {
                    "access_token": session.access_token,
                    "refresh_token": session.refresh_token,
                    "phone_number": session.phone_number,
                    "telegram_id": session.telegram_id,
                    "saved_at": session.saved_at,
                }
                for key, session in self._sessions.items()
            }
        }
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _store_session(
        self,
        telegram_id: int,
        access_token: str,
        refresh_token: str | None,
        phone_number: str,
    ) -> None:
        session = AuthSession(
            access_token=access_token,
            refresh_token=refresh_token,
            phone_number=phone_number,
            telegram_id=telegram_id,
            saved_at=datetime.now(timezone.utc).isoformat(),
        )
        self._sessions[self._key(telegram_id)] = session
        self._save()

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
        async with httpx.AsyncClient(timeout=15.0) as client:
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
        if not token:
            return False

        url = f"{self._base_url}/users/me"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
        return response.status_code == 200

    async def fetch_me(self, token: str) -> dict[str, Any]:
        url = f"{self._base_url}/users/me"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
        if response.status_code >= 400:
            raise AuthError("Profilni olishda xatolik")
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    async def send_otp(self, phone_number: str) -> str:
        phone = normalize_phone(phone_number)
        payload = await self._post_json(
            "/auth/send-otp",
            {"phone_number": phone},
        )
        message = payload.get("message") if isinstance(payload, dict) else None
        if message:
            return str(message)
        return f"SMS kod {format_phone_display(phone)} raqamiga yuborildi."

    async def verify_otp(
        self, telegram_id: int, phone_number: str, code: str
    ) -> AuthSession:
        phone = normalize_phone(phone_number)
        code = code.strip()
        if not re.fullmatch(r"\d{4,6}", code):
            raise AuthError("Kod 4-6 ta raqamdan iborat bo'lishi kerak")

        payload = await self._post_json(
            self.VERIFY_ENDPOINT,
            {"phone_number": phone, "otp_code": code},
        )

        access_token, refresh_token = self._extract_token(payload)
        if not access_token:
            raise AuthError("OTP tasdiqlanmadi: token qaytmadi")

        me = await self.fetch_me(access_token)
        if me.get("is_active") is False:
            raise AuthError("Bu akkaunt nofaol")

        self._store_session(telegram_id, access_token, refresh_token, phone)
        session = self.get_session(telegram_id)
        assert session is not None
        return session

    async def refresh_access_token(self, telegram_id: int) -> bool:
        session = self.get_session(telegram_id)
        if not session or not session.refresh_token:
            return False

        try:
            payload = await self._post_json(
                self.REFRESH_ENDPOINT,
                {"refresh_token": session.refresh_token},
            )
        except AuthError as exc:
            logger.warning("Token refresh failed for %s: %s", telegram_id, exc)
            return False

        access_token, refresh_token = self._extract_token(payload)
        if access_token:
            self._store_session(
                telegram_id,
                access_token,
                refresh_token or session.refresh_token,
                session.phone_number or "",
            )
            return True
        return False

    async def ensure_access_token(self, telegram_id: int | None = None) -> str:
        if self._static_token:
            return self._static_token

        if telegram_id is not None:
            token = self.get_access_token(telegram_id)
            if token and await self.validate_token(token):
                return token
            if await self.refresh_access_token(telegram_id):
                token = self.get_access_token(telegram_id)
                if token and await self.validate_token(token):
                    return token
            raise OTPRequired("Login qiling: /login")

        # Background: try any session
        for key in list(self._sessions.keys()):
            tid = int(key) if key.isdigit() else None
            if tid is None:
                continue
            try:
                return await self.ensure_access_token(tid)
            except OTPRequired:
                continue

        raise OTPRequired("Hech qaysi moderator login qilmagan.")

    async def invalidate(self, telegram_id: int | None = None) -> None:
        if telegram_id is None:
            self._sessions.clear()
            self._save()
            return
        self._sessions.pop(self._key(telegram_id), None)
        self._save()
