from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.api_client import ArenaTopAPIError
from bot.auth import format_phone_display
from bot.keyboards import (
    BTN_BOOKINGS,
    BTN_COURTS,
    BTN_PAYMENTS,
    BTN_PROFILE,
    BTN_SETTINGS,
    BTN_STATS,
    MAIN_MENU,
    MENU_BUTTONS,
    bookings_menu_keyboard,
    payments_menu_keyboard,
    refresh_keyboard,
    settings_menu_keyboard,
    stats_menu_keyboard,
)
from bot.login_flow import begin_login_for_user, handle_login_text, is_login_in_progress
from bot.notifier import PaymentNotifier
from bot.stats_formatters import (
    format_bookings_list,
    format_courts_list,
    format_dashboard_stats,
    format_payments_overview,
    format_profile,
    format_today_stats,
    format_users_summary,
)

logger = logging.getLogger(__name__)

BOOKING_TITLES = {
    "pending": "⏳ <b>Kutilayotgan bronlar</b>",
    "confirmed": "✅ <b>Tasdiqlangan bronlar</b>",
    "completed": "🏁 <b>Tugallangan bronlar</b>",
    "cancelled": "❌ <b>Bekor qilingan bronlar</b>",
    "all": "📋 <b>Barcha bronlar</b>",
}


from bot.ui_utils import (
    get_api,
    get_auth,
    get_settings,
    is_admin,
    require_login,
    send_message,
)
from bot.process_flow import (
    has_pending,
    process_callback_handler,
    send_refund_items,
    send_withdrawal_items,
)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return

    auth = get_auth(context)
    user = update.effective_user
    phone = auth.phone_for(user.id) if user else None
    phone_line = (
        f"📱 {format_phone_display(phone)}" if phone else "📱 Telefon: —"
    )

    await send_message(
        update,
        "\n".join(
            [
                "🏠 <b>ArenaTop Admin Panel</b>",
                "",
                "Asosiy funksiya — pul so'rovlarini kuzatish.",
                "🔐 Login: faol",
                phone_line,
                "",
                "Quyidagi tugmalardan foydalaning 👇",
            ]
        ),
        reply_keyboard=MAIN_MENU,
    )


async def show_payments_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    api = get_api(context)
    settings = get_settings(context)
    try:
        refunds = await api.get_refund_requests(settings.refund_statuses)
        withdrawals = await api.get_withdrawal_requests(settings.withdrawal_statuses)
        text = format_payments_overview(refunds, withdrawals)
    except ArenaTopAPIError as exc:
        text = f"💰 <b>Pul so'rovlari</b>\n\nAPI xatolik: {exc}"

    await send_message(update, text, keyboard=payments_menu_keyboard())


async def show_refunds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    api = get_api(context)
    settings = get_settings(context)
    try:
        items = await api.get_refund_requests(settings.refund_statuses)
        await send_refund_items(update, context, items)
    except ArenaTopAPIError as exc:
        await send_message(update, f"API xatolik: {exc}", keyboard=refresh_keyboard("pay:refunds"))


async def show_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    api = get_api(context)
    settings = get_settings(context)
    try:
        items = await api.get_withdrawal_requests(settings.withdrawal_statuses)
        await send_withdrawal_items(update, context, items)
    except ArenaTopAPIError as exc:
        await send_message(update, f"API xatolik: {exc}", keyboard=refresh_keyboard("pay:withdrawals"))


async def show_all_payments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    api = get_api(context)
    try:
        refunds = await api.get_refund_requests(None)
        withdrawals = await api.get_withdrawal_requests(None)
        text = format_payments_overview(refunds, withdrawals)
        text += "\n\n🔁 Qaytarishlar: barcha holatlar\n💸 Yechishlar: barcha holatlar"
    except ArenaTopAPIError as exc:
        text = f"API xatolik: {exc}"
    await send_message(update, text, keyboard=payments_menu_keyboard())


async def check_payments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    notifier: PaymentNotifier = context.application.bot_data["notifier"]
    try:
        result = await notifier.check_and_notify(context.application)
        text = (
            "🔄 <b>Tekshiruv yakunlandi</b>\n\n"
            f"Yangi qaytarishlar: <b>{result['refunds']}</b>\n"
            f"Yangi yechishlar: <b>{result['withdrawals']}</b>"
        )
    except ArenaTopAPIError as exc:
        text = f"API xatolik: {exc}"
    await send_message(update, text, keyboard=payments_menu_keyboard())


async def show_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    await send_message(
        update,
        "📊 <b>Statistika</b>\n\nKerakli bo'limni tanlang:",
        keyboard=stats_menu_keyboard(),
    )


async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    api = get_api(context)
    try:
        data = await api.get_dashboard_stats()
        text = format_dashboard_stats(data)
    except ArenaTopAPIError as exc:
        text = f"API xatolik: {exc}"
    await send_message(update, text, keyboard=refresh_keyboard("stats:dashboard"))


async def show_users_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    api = get_api(context)
    try:
        data = await api.get_users_summary()
        text = format_users_summary(data)
    except ArenaTopAPIError as exc:
        text = f"API xatolik: {exc}"
    await send_message(update, text, keyboard=refresh_keyboard("stats:users"))


async def show_today_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    api = get_api(context)
    try:
        data = await api.get_my_statistics()
        text = format_today_stats(data)
    except ArenaTopAPIError as exc:
        text = f"API xatolik: {exc}"
    await send_message(update, text, keyboard=refresh_keyboard("stats:today"))


async def show_bookings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    await send_message(
        update,
        "📋 <b>Bronlar</b>\n\nHolat bo'yicha tanlang:",
        keyboard=bookings_menu_keyboard(),
    )


async def show_bookings(
    update: Update, context: ContextTypes.DEFAULT_TYPE, status: str | None
) -> None:
    if not await require_login(update, context):
        return
    api = get_api(context)
    title = BOOKING_TITLES.get(status or "all", "📋 <b>Bronlar</b>")
    callback = f"book:{status or 'all'}"
    try:
        items = await api.get_bookings(status=None if status == "all" else status)
        text = format_bookings_list(items, title)
    except ArenaTopAPIError as exc:
        text = f"API xatolik: {exc}"
    await send_message(update, text, keyboard=refresh_keyboard(callback))


async def show_courts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    api = get_api(context)
    try:
        items = await api.get_courts()
        text = format_courts_list(items)
    except ArenaTopAPIError as exc:
        text = f"API xatolik: {exc}"
    await send_message(update, text, keyboard=refresh_keyboard("menu:courts"))


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    api = get_api(context)
    try:
        data = await api.get_me()
        text = format_profile(data)
    except ArenaTopAPIError as exc:
        text = f"API xatolik: {exc}"
    await send_message(update, text, keyboard=refresh_keyboard("menu:profile"))


async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    await send_message(
        update,
        "⚙️ <b>Sozlamalar</b>",
        keyboard=settings_menu_keyboard(),
    )


async def show_bot_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    settings = get_settings(context)
    notifier: PaymentNotifier = context.application.bot_data["notifier"]
    auth = get_auth(context)
    user = update.effective_user
    counts = notifier.storage_counts()
    phone = auth.phone_for(user.id) if user else None
    phone_text = format_phone_display(phone) if phone else "—"

    text = "\n".join(
        [
            "🤖 <b>Bot holati</b>",
            "",
            "✅ Ishlayapti",
            f"🌐 API: {settings.api_base_url}",
            f"📱 Telefon: {phone_text}",
            "🔐 Login: faol",
            f"⏱ Tekshirish: har {settings.poll_interval_seconds} soniya",
            f"📨 Yuborilgan: {counts['refunds']} qaytarish, "
            f"{counts['withdrawals']} yechish",
        ]
    )
    await send_message(update, text, keyboard=settings_menu_keyboard())


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    text = "\n".join(
        [
            "❓ <b>Yordam</b>",
            "",
            "Bot asosan pul qaytarish va yechish so'rovlarini kuzatadi.",
            "Yangi so'rov kelganda avtomatik xabar yuboriladi.",
            "",
            "<b>Login:</b>",
            "1. /login — telefon raqamingizni yuboring",
            "2. SMS dagi kodni yuboring",
            "3. Panel ochiladi",
            "",
            "<b>Bo'limlar:</b>",
            "💰 Pul so'rovlari — qaytarish va yechish",
            "📊 Statistika — dashboard va foydalanuvchilar",
            "📋 Bronlar — platforma bronlari",
            "🏟 Maydonlar — barcha maydonlar",
            "👤 Profil — sizning akkauntingiz",
            "",
            f"Tekshirish intervali: {settings.poll_interval_seconds} soniya",
        ]
    )
    await send_message(update, text, keyboard=settings_menu_keyboard())


async def handle_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await begin_login_for_user(update, context)


CALLBACK_ROUTES = {
    "menu:main": show_main_menu,
    "menu:payments": show_payments_menu,
    "menu:stats": show_stats_menu,
    "menu:bookings": show_bookings_menu,
    "menu:courts": show_courts,
    "menu:profile": show_profile,
    "menu:settings": show_settings_menu,
    "pay:refunds": show_refunds,
    "pay:withdrawals": show_withdrawals,
    "pay:all": show_all_payments,
    "pay:check": check_payments,
    "stats:dashboard": show_dashboard,
    "stats:users": show_users_stats,
    "stats:today": show_today_stats,
    "book:pending": lambda u, c: show_bookings(u, c, "pending"),
    "book:confirmed": lambda u, c: show_bookings(u, c, "confirmed"),
    "book:completed": lambda u, c: show_bookings(u, c, "completed"),
    "book:cancelled": lambda u, c: show_bookings(u, c, "cancelled"),
    "book:all": lambda u, c: show_bookings(u, c, "all"),
    "set:status": show_bot_status,
    "set:login": handle_login,
    "set:help": show_help,
}

BUTTON_ROUTES = {
    BTN_PAYMENTS: show_payments_menu,
    BTN_STATS: show_stats_menu,
    BTN_BOOKINGS: show_bookings_menu,
    BTN_COURTS: show_courts,
    BTN_PROFILE: show_profile,
    BTN_SETTINGS: show_settings_menu,
}


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    user = update.effective_user
    if not is_admin(user.id if user else None, settings):
        if update.callback_query:
            await update.callback_query.answer("Ruxsat yo'q", show_alert=True)
        return

    data = update.callback_query.data if update.callback_query else ""
    logger.info("Callback: %s", data)

    # Login / cancel process can run without full session for set:login
    if data == "set:login":
        await handle_login(update, context)
        return

    try:
        if await process_callback_handler(update, context, data):
            return

        if not await require_login(update, context):
            return

        handler = CALLBACK_ROUTES.get(data)
        if handler:
            await handler(update, context)
        elif update.callback_query:
            await update.callback_query.answer("Noma'lum buyruq", show_alert=True)
    except Exception:
        logger.exception("Callback handler error for %s", data)
        if update.callback_query:
            await update.callback_query.answer("Xatolik yuz berdi", show_alert=True)


async def menu_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    user = update.effective_user
    if not is_admin(user.id if user else None, settings):
        return
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    handler = BUTTON_ROUTES.get(text)
    if handler:
        await handler(update, context)


async def otp_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    user = update.effective_user

    if not update.message or not update.message.text:
        return
    if not is_admin(user.id if user else None, settings):
        return

    text = update.message.text.strip()
    if text in MENU_BUTTONS:
        return
    if has_pending(context):
        return

    if await handle_login_text(update, context):
        return

    if is_login_in_progress(context):
        return

