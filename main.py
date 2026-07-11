from __future__ import annotations

import logging
import sys

print("Kutubxonalar yuklanmoqda (10-20 soniya)...", flush=True)

from bot.api_client import ArenaTopClient
from bot.auth import AuthService
from bot.config import Settings
from bot.handlers import build_application
from bot.notifier import PaymentNotifier
from bot.storage import SeenStorage

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    force=True,
)
logger = logging.getLogger(__name__)


def main() -> None:
    print("ArenaTop bot ishga tushmoqda...", flush=True)

    try:
        settings = Settings.from_env()
    except ValueError as exc:
        print(f"Xatolik: {exc}", flush=True)
        print("Yechim: .env.example dan .env faylini yarating.", flush=True)
        sys.exit(1)

    print("Sozlamalar yuklandi.", flush=True)

    auth = AuthService(
        base_url=settings.api_base_url,
        storage_path=settings.auth_storage_path,
        static_token=settings.api_token,
    )
    api_client = ArenaTopClient(settings.api_base_url, auth)
    storage = SeenStorage(settings.storage_path)
    notifier = PaymentNotifier(settings, api_client, storage)

    print("Telegram bot yaratilmoqda...", flush=True)
    application = build_application(settings, notifier, auth, api_client)

    print("Telegram ga ulanilmoqda...", flush=True)
    logger.info("Starting ArenaTop admin bot...")
    print(
        "Bot ishlayapti. Terminal qotib qolgandek tuyulishi normal.\n"
        "To'xtatish uchun: Ctrl+C\n"
        "Moderatorlar: /start → telefon → SMS kod.",
        flush=True,
    )
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
