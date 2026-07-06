from __future__ import annotations

import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot.api_client import ArenaTopClient
from bot.config import Settings

logger = logging.getLogger(__name__)


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

    if update.callback_query:
        await update.callback_query.answer()

        # Reply keyboard faqat yangi xabar bilan yuboriladi
        if reply_keyboard is not None:
            kwargs["reply_markup"] = reply_keyboard
            if update.callback_query.message:
                await update.callback_query.message.reply_text(text, **kwargs)
            return

        if keyboard is not None:
            kwargs["reply_markup"] = keyboard

        if not update.callback_query.message:
            return

        try:
            await update.callback_query.edit_message_text(text, **kwargs)
        except BadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return
            logger.warning("Edit failed, sending new message: %s", exc)
            await update.callback_query.message.reply_text(text, **kwargs)
        except Exception:
            logger.exception("Callback message send failed")
            await update.callback_query.message.reply_text(text, **kwargs)
        return

    if update.message:
        if reply_keyboard is not None:
            kwargs["reply_markup"] = reply_keyboard
        elif keyboard is not None:
            kwargs["reply_markup"] = keyboard
        await update.message.reply_text(text, **kwargs)
