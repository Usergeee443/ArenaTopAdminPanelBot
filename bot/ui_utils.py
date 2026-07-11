from __future__ import annotations

import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot.api_client import ArenaTopClient
from bot.auth import AuthService
from bot.config import Settings

logger = logging.getLogger(__name__)


def get_settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.application.bot_data["settings"]


def get_auth(context: ContextTypes.DEFAULT_TYPE) -> AuthService:
    return context.application.bot_data["auth"]


def bind_user(context: ContextTypes.DEFAULT_TYPE, telegram_id: int | None) -> None:
    if telegram_id is None:
        context.user_data.pop("_active_telegram_id", None)
    else:
        context.user_data["_active_telegram_id"] = telegram_id


def get_api(context: ContextTypes.DEFAULT_TYPE) -> ArenaTopClient:
    api: ArenaTopClient = context.application.bot_data["api"]
    telegram_id = context.user_data.get("_active_telegram_id")
    if telegram_id is not None:
        return api.for_user(int(telegram_id))
    return api


def can_access_bot(user_id: int | None, settings: Settings) -> bool:
    if user_id is None:
        return False
    if not settings.admin_telegram_ids:
        return True
    return user_id in settings.admin_telegram_ids


def is_logged_in(user_id: int | None, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if user_id is None:
        return False
    return get_auth(context).is_logged_in(user_id)


def is_admin(user_id: int | None, settings: Settings) -> bool:
    return can_access_bot(user_id, settings)


async def require_login(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    settings = get_settings(context)
    user = update.effective_user
    if not can_access_bot(user.id if user else None, settings):
        if update.callback_query:
            await update.callback_query.answer("Ruxsat yo'q", show_alert=True)
        elif update.message:
            await update.message.reply_text(
                "Bu bot faqat ArenaTop moderatorlari uchun.\n"
                f"Sizning Telegram ID: {user.id if user else '—'}"
            )
        return False

    if user and is_logged_in(user.id, context):
        bind_user(context, user.id)
        return True

    from bot.login_flow import prompt_phone_login

    if update.callback_query:
        await update.callback_query.answer("Avval login qiling", show_alert=True)
    await prompt_phone_login(update, context)
    return False


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
