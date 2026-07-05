from __future__ import annotations

import asyncio
import logging

from telegram.ext import Application

from bot.config import Settings
from bot.notifier import PaymentNotifier

logger = logging.getLogger(__name__)


async def bootstrap_notifier(application: Application) -> None:
    if application.bot_data.get("notifier_started"):
        return

    notifier: PaymentNotifier = application.bot_data["notifier"]
    settings: Settings = application.bot_data["settings"]

    application.bot_data["notifier_started"] = True
    logger.info("Seeding existing requests...")
    await notifier.seed_existing_requests()
    logger.info(
        "Background polling started (every %s seconds).",
        settings.poll_interval_seconds,
    )
    asyncio.create_task(notifier.run_polling_loop(application))
