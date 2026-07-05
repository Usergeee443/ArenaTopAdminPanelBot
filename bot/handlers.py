from __future__ import annotations

import asyncio
import logging

import re

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.api_client import ArenaTopClient
from bot.auth import AuthService, OTPRequired
from bot.config import Settings
from bot.keyboards import MENU_BUTTONS
from bot.bootstrap import bootstrap_notifier
from bot.login_flow import begin_login
from bot.menu import (
    callback_handler,
    check_payments,
    handle_login,
    menu_button_handler,
    otp_message_handler,
    show_help,
    show_main_menu,
    show_payments_menu,
)
from bot.process_flow import has_pending, submit_receipt
from bot.notifier import PaymentNotifier

logger = logging.getLogger(__name__)


async def startup_flow(application: Application) -> None:
    auth: AuthService = application.bot_data["auth"]

    try:
        await auth.ensure_access_token()
        await bootstrap_notifier(application)
        return
    except OTPRequired:
        logger.info("Valid API token not found. Starting phone login...")
        await begin_login(application)
    except Exception:
        logger.exception("Startup auth failed")


async def post_init(application: Application) -> None:
    print("Bot tayyor. ArenaTop API ga ulanish boshlandi...", flush=True)
    asyncio.create_task(startup_flow(application))


async def start_command(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    user = update.effective_user
    if user and user.id not in settings.admin_telegram_ids:
        if update.message:
            await update.message.reply_text(
                "Bu bot faqat ArenaTop adminlari uchun.\n"
                f"Sizning Telegram ID: {user.id}"
            )
        return
    await show_main_menu(update, context)


def build_application(
    settings: Settings,
    notifier: PaymentNotifier,
    auth: AuthService,
    api: ArenaTopClient,
) -> Application:
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .build()
    )

    application.bot_data["settings"] = settings
    application.bot_data["notifier"] = notifier
    application.bot_data["auth"] = auth
    application.bot_data["api"] = api
    application.bot_data["notifier_started"] = False

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", start_command))
    application.add_handler(CommandHandler("help", show_help))
    application.add_handler(CommandHandler("login", handle_login))
    application.add_handler(CommandHandler("pending", show_payments_menu))
    application.add_handler(CommandHandler("check", check_payments))
    application.add_handler(CallbackQueryHandler(callback_handler))
    menu_pattern = "^(" + "|".join(re.escape(btn) for btn in MENU_BUTTONS) + ")$"
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(menu_pattern),
            menu_button_handler,
        )
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, otp_message_handler)
    )
    application.add_handler(
        MessageHandler(
            (filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
            receipt_handler,
        )
    )

    return application


async def receipt_handler(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    user = update.effective_user
    if not user or user.id not in settings.admin_telegram_ids:
        return
    if has_pending(context):
        await submit_receipt(update, context)
