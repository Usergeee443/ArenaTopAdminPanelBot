from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    root = Path(__file__).resolve().parent.parent
    env_file = root / ".env"
    example_file = root / ".env.example"

    if env_file.exists():
        load_dotenv(env_file)
    elif example_file.exists():
        load_dotenv(example_file)
    else:
        load_dotenv()


_load_env()


def _parse_int_list(raw: str) -> list[int]:
    values: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        values.append(int(part))
    return values


def _parse_str_list(raw: str) -> list[str]:
    return [part.strip().lower() for part in raw.split(",") if part.strip()]


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    admin_telegram_ids: list[int]
    api_base_url: str
    api_token: str | None
    poll_interval_seconds: int
    refund_statuses: list[str]
    withdrawal_statuses: list[str]
    storage_path: str
    auth_storage_path: str
    report_timezone: str
    daily_report_hour: int
    daily_report_minute: int

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")

        # Optional allowlist. Empty = any moderator who OTP-logs in can use the bot.
        admin_ids = _parse_int_list(os.getenv("ADMIN_TELEGRAM_IDS", ""))

        api_token = os.getenv("ARENATOP_API_TOKEN", "").strip() or None

        base_url = os.getenv(
            "ARENATOP_API_BASE_URL", "https://api.arenatop.uz/v1"
        ).rstrip("/")

        poll_interval = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
        if poll_interval < 15:
            poll_interval = 15

        report_timezone = os.getenv("REPORT_TIMEZONE", "Asia/Tashkent").strip()
        daily_report_hour = int(os.getenv("DAILY_REPORT_HOUR", "0"))
        daily_report_minute = int(os.getenv("DAILY_REPORT_MINUTE", "0"))
        if not 0 <= daily_report_hour <= 23:
            daily_report_hour = 0
        if not 0 <= daily_report_minute <= 59:
            daily_report_minute = 0

        return cls(
            telegram_bot_token=token,
            admin_telegram_ids=admin_ids,
            api_base_url=base_url,
            api_token=api_token,
            poll_interval_seconds=poll_interval,
            refund_statuses=_parse_str_list(
                os.getenv("REFUND_STATUSES", "pending")
            ),
            withdrawal_statuses=_parse_str_list(
                os.getenv("WITHDRAWAL_STATUSES", "pending")
            ),
            storage_path=os.getenv("STORAGE_PATH", "data/seen_requests.json"),
            auth_storage_path=os.getenv(
                "AUTH_STORAGE_PATH", "data/auth_sessions.json"
            ),
            report_timezone=report_timezone or "Asia/Tashkent",
            daily_report_hour=daily_report_hour,
            daily_report_minute=daily_report_minute,
        )
