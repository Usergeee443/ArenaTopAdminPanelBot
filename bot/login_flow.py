from __future__ import annotations

import logging

from telegram.ext import Application

from bot.auth import AuthError, AuthService, format_phone_display
from bot.config import Settings

logger = logging.getLogger(__name__)


async def notify_admins(application: Application, text: str) -> None:
    settings: Settings = application.bot_data["settings"]
    for admin_id in settings.admin_telegram_ids:
        try:
            await application.bot.send_message(chat_id=admin_id, text=text)
        except Exception:
            logger.exception("Failed to notify admin %s", admin_id)


async def begin_login(application: Application) -> None:
    auth: AuthService = application.bot_data["auth"]
    settings: Settings = application.bot_data["settings"]

    try:
        message = await auth.send_otp()
    except AuthError as exc:
        await notify_admins(
            application,
            f"ArenaTop login xatolik:\n{exc}\n\n/login buyrug'i bilan qayta urinib ko'ring.",
        )
        return

    await notify_admins(
        application,
        f"🔐 ArenaTop login\n\n{message}\n\n"
        f"Telefon: {format_phone_display(auth.phone_number)}\n"
        "SMS kelgan kodni shu yerga yuboring (masalan: 123456).",
    )
