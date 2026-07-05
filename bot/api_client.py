from __future__ import annotations

from typing import Any

import httpx

from bot.auth import AuthService, OTPRequired
from bot.formatters import extract_item_id, extract_refund_status, extract_status


class ArenaTopAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ArenaTopClient:
    REFUND_ENDPOINT = "/refund-requests"
    WITHDRAWAL_ENDPOINT = "/withdrawals"

    def __init__(self, base_url: str, auth: AuthService) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = auth

    async def _auth_headers(self) -> dict[str, str]:
        try:
            token = await self._auth.ensure_access_token()
        except OTPRequired as exc:
            raise ArenaTopAPIError(str(exc), 401) from exc

        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    async def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        headers = await self._auth_headers()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)

        if response.status_code == 401:
            await self._auth.invalidate()
            raise ArenaTopAPIError("API token noto'g'ri yoki muddati tugagan", 401)
        if response.status_code == 403:
            raise ArenaTopAPIError("API uchun ruxsat yo'q", 403)
        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise ArenaTopAPIError(
                f"API xatolik ({response.status_code}): {detail}",
                response.status_code,
            )

        if not response.content:
            return []
        return response.json()

    @staticmethod
    def _unwrap_items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if not isinstance(payload, dict):
            return []

        for key in ("items", "results", "data", "requests", "refunds", "withdrawals"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        return []

    @staticmethod
    def _filter_refunds(
        items: list[dict[str, Any]], allowed_statuses: list[str]
    ) -> list[dict[str, Any]]:
        if not allowed_statuses:
            return items

        allowed = {status.lower() for status in allowed_statuses}
        return [
            item
            for item in items
            if extract_refund_status(item).lower() in allowed
        ]

    @staticmethod
    def _filter_withdrawals(
        items: list[dict[str, Any]], allowed_statuses: list[str]
    ) -> list[dict[str, Any]]:
        if not allowed_statuses:
            return items

        allowed = {status.lower() for status in allowed_statuses}
        return [
            item
            for item in items
            if extract_status(item).lower() in allowed
        ]

    @staticmethod
    def _dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for item in items:
            item_id = extract_item_id(item)
            if not item_id or item_id in seen:
                continue
            seen.add(item_id)
            unique.append(item)
        return unique

    async def get_refund_requests(
        self, allowed_statuses: list[str] | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": 100}
        if allowed_statuses and len(allowed_statuses) == 1:
            params["refund_status"] = allowed_statuses[0]

        payload = await self._request(self.REFUND_ENDPOINT, params=params)
        items = self._dedupe_items(self._unwrap_items(payload))
        if allowed_statuses is not None and len(allowed_statuses) != 1:
            items = self._filter_refunds(items, allowed_statuses)
        return items

    async def get_withdrawal_requests(
        self, allowed_statuses: list[str] | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"scope": "platform", "limit": 100}
        if allowed_statuses and len(allowed_statuses) == 1:
            params["status"] = allowed_statuses[0]

        payload = await self._request(self.WITHDRAWAL_ENDPOINT, params=params)
        items = self._dedupe_items(self._unwrap_items(payload))
        if allowed_statuses is not None and len(allowed_statuses) != 1:
            items = self._filter_withdrawals(items, allowed_statuses)
        return items

    async def get_dashboard_stats(self) -> dict[str, Any]:
        payload = await self._request("/settings/dashboard")
        return payload if isinstance(payload, dict) else {}

    async def get_users_summary(self) -> dict[str, Any]:
        payload = await self._request("/users/summary")
        return payload if isinstance(payload, dict) else {}

    async def get_my_statistics(self) -> dict[str, Any]:
        payload = await self._request("/users/me/statistics")
        return payload if isinstance(payload, dict) else {}

    async def get_me(self) -> dict[str, Any]:
        payload = await self._request("/users/me")
        return payload if isinstance(payload, dict) else {}

    async def get_bookings(
        self, status: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"scope": "platform", "limit": limit}
        if status:
            params["status"] = status
        payload = await self._request("/bookings", params=params)
        return self._unwrap_items(payload)

    async def get_courts(self, limit: int = 20) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"scope": "all", "limit": limit}
        payload = await self._request("/courts", params=params)
        return self._unwrap_items(payload)

    async def health_check(self) -> str:
        payload = await self.get_me()
        if payload:
            name = payload.get("name") or payload.get("full_name")
            role = payload.get("role")
            parts = ["API ulanishi muvaffaqiyatli."]
            if name:
                parts.append(f"Foydalanuvchi: {name}")
            if role:
                parts.append(f"Rol: {role}")
            return "\n".join(parts)
        return "API ulanishi muvaffaqiyatli."

    async def _post_multipart(
        self,
        path: str,
        data: dict[str, str],
        file_field: str,
        file_bytes: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
    ) -> Any:
        url = f"{self._base_url}{path}"
        headers = await self._auth_headers()
        files = {file_field: (filename, file_bytes, content_type)}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url, headers=headers, data=data, files=files
            )

        if response.status_code == 401:
            await self._auth.invalidate()
            raise ArenaTopAPIError("API token noto'g'ri yoki muddati tugagan", 401)
        if response.status_code == 403:
            raise ArenaTopAPIError("API uchun ruxsat yo'q", 403)
        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise ArenaTopAPIError(
                f"API xatolik ({response.status_code}): {detail}",
                response.status_code,
            )

        if not response.content:
            return {}
        return response.json()

    async def _post_form(self, path: str, data: dict[str, str]) -> Any:
        url = f"{self._base_url}{path}"
        headers = await self._auth_headers()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, data=data)

        if response.status_code == 401:
            await self._auth.invalidate()
            raise ArenaTopAPIError("API token noto'g'ri yoki muddati tugagan", 401)
        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise ArenaTopAPIError(
                f"API xatolik ({response.status_code}): {detail}",
                response.status_code,
            )

        if not response.content:
            return {}
        return response.json()

    async def process_refund_request(
        self,
        booking_id: str,
        status: str,
        receipt_bytes: bytes | None = None,
        filename: str = "receipt.jpg",
        content_type: str = "image/jpeg",
        note: str | None = None,
    ) -> dict[str, Any]:
        path = f"/refund-requests/{booking_id}/process"
        form: dict[str, str] = {"status": status}
        if note:
            form["note"] = note

        if receipt_bytes:
            payload = await self._post_multipart(
                path, form, "receipt", receipt_bytes, filename, content_type
            )
        else:
            payload = await self._post_form(path, form)

        return payload if isinstance(payload, dict) else {}

    async def process_withdrawal(
        self,
        withdrawal_id: str,
        status: str,
        receipt_bytes: bytes | None = None,
        filename: str = "receipt.jpg",
        content_type: str = "image/jpeg",
        note: str | None = None,
    ) -> dict[str, Any]:
        path = f"/withdrawals/{withdrawal_id}/process"
        form: dict[str, str] = {"status": status}
        if note:
            form["note"] = note

        if receipt_bytes:
            payload = await self._post_multipart(
                path, form, "receipt", receipt_bytes, filename, content_type
            )
        else:
            payload = await self._post_form(path, form)

        return payload if isinstance(payload, dict) else {}
