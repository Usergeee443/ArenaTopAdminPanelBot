from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.api_client import ArenaTopClient
from bot.config import Settings


def is_admin(user_id: int | None, settings: Settings) -> bool:
    return user_id is not None and user_id in settings.admin_telegram_ids


def get_api(context: ContextTypes.DEFAULT_TYPE) -> ArenaTopClient:
    return context.application.bot_data["api"]


def get_settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.application.bot_data["settings"]


async def send_message(
    update: Update,
    text: str,
    *,
    keyboard=None,
    reply_keyboard=None,
) -> None:
    kwargs: dict = {
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if keyboard is not None:
        kwargs["reply_markup"] = keyboard
    if reply_keyboard is not None:
        kwargs["reply_markup"] = reply_keyboard

    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(text, **kwargs)
        except Exception:
            if update.callback_query.message:
                await update.callback_query.message.reply_text(text, **kwargs)
    elif update.message:
        await update.message.reply_text(text, **kwargs)
