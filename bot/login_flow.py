from __future__ import annotations

import logging
import re

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import Application, ContextTypes

from bot.auth import (
    AuthError,
    AuthService,
    format_phone_display,
    looks_like_phone,
    normalize_phone,
)
from bot.bootstrap import bootstrap_notifier
from bot.keyboards import MAIN_MENU

logger = logging.getLogger(__name__)

LOGIN_STEP_KEY = "login_step"
LOGIN_PHONE_KEY = "login_phone"

STEP_PHONE = "phone"
STEP_OTP = "otp"


def get_auth(context: ContextTypes.DEFAULT_TYPE) -> AuthService:
    return context.application.bot_data["auth"]


def clear_login_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(LOGIN_STEP_KEY, None)
    context.user_data.pop(LOGIN_PHONE_KEY, None)


def is_login_in_progress(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return context.user_data.get(LOGIN_STEP_KEY) in {STEP_PHONE, STEP_OTP}


async def notify_admins(application: Application, text: str) -> None:
    """Notify allowlisted IDs and currently logged-in moderators."""
    settings = application.bot_data["settings"]
    auth: AuthService = application.bot_data["auth"]

    recipients = set(settings.admin_telegram_ids)
    recipients.update(auth.logged_in_telegram_ids())

    for admin_id in recipients:
        try:
            await application.bot.send_message(chat_id=admin_id, text=text)
        except Exception:
            logger.exception("Failed to notify admin %s", admin_id)


async def prompt_phone_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_login_state(context)
    context.user_data[LOGIN_STEP_KEY] = STEP_PHONE

    text = (
        "🔐 <b>ArenaTop login</b>\n\n"
        "Moderator telefon raqamingizni yuboring.\n"
        "Masalan: <code>917079732</code> yoki <code>+998 91 707 97 32</code>"
    )
    if update.message:
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )


async def begin_login_for_user(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await prompt_phone_login(update, context)


async def handle_login_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """Handle phone/OTP messages during interactive login. Returns True if handled."""
    if not update.message or not update.message.text:
        return False

    step = context.user_data.get(LOGIN_STEP_KEY)
    if step not in {STEP_PHONE, STEP_OTP}:
        return False

    user = update.effective_user
    if not user:
        return False

    text = update.message.text.strip()
    auth = get_auth(context)

    if step == STEP_PHONE:
        if not looks_like_phone(text):
            await update.message.reply_text(
                "Telefon raqami noto'g'ri.\n"
                "Masalan: <code>917079732</code>",
                parse_mode="HTML",
            )
            return True

        try:
            phone = normalize_phone(text)
            message = await auth.send_otp(phone)
        except AuthError as exc:
            await update.message.reply_text(f"Login xatolik:\n{exc}")
            return True

        context.user_data[LOGIN_PHONE_KEY] = phone
        context.user_data[LOGIN_STEP_KEY] = STEP_OTP
        await update.message.reply_text(
            f"{message}\n\n"
            f"📱 Telefon: <b>{format_phone_display(phone)}</b>\n\n"
            "SMS dagi tasdiqlash kodini yuboring (masalan: <code>123456</code>).",
            parse_mode="HTML",
        )
        return True

    # STEP_OTP
    if not re.fullmatch(r"\d{4,6}", text):
        await update.message.reply_text(
            "Kod 4-6 ta raqamdan iborat bo'lishi kerak.\n"
            "Qayta urinib ko'ring yoki /login bosing."
        )
        return True

    phone = context.user_data.get(LOGIN_PHONE_KEY)
    if not phone:
        await prompt_phone_login(update, context)
        return True

    await update.message.reply_text("Kod tekshirilmoqda...")

    try:
        session = await auth.verify_otp(user.id, phone, text)
    except AuthError as exc:
        await update.message.reply_text(
            f"Login xatolik:\n{exc}\n\n"
            "Qayta urinish: /login"
        )
        return True

    clear_login_state(context)

    display = format_phone_display(session.phone_number or phone)
    await update.message.reply_text(
        f"✅ Muvaffaqiyatli kirdingiz!\n\n"
        f"📱 {display}\n\n"
        "Endi admin paneldan foydalanishingiz mumkin.",
        reply_markup=MAIN_MENU,
    )

    try:
        await bootstrap_notifier(context.application)
    except Exception:
        logger.exception("Failed to bootstrap notifier after login")

    return True


# Backward-compatible name used by notifier on 401
async def begin_login(application: Application) -> None:
    await notify_admins(
        application,
        "🔐 API sessiyasi tugagan.\n"
        "Har bir moderator /login orqali qayta kirishi kerak.",
    )
