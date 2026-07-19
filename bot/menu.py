from __future__ import annotations

import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from bot.api_client import ArenaTopAPIError
from bot.auth import format_phone_display
from bot.keyboards import (
    BTN_BOOKINGS,
    BTN_COURTS,
    BTN_PAYMENTS,
    BTN_PROFILE,
    BTN_PROFILE_SETTINGS,
    BTN_SETTINGS,
    BTN_STATS,
    MAIN_MENU,
    MENU_BUTTONS,
    bookings_menu_keyboard,
    court_confirm_keyboard,
    court_details_keyboard,
    courts_list_keyboard,
    months_menu_keyboard,
    payments_menu_keyboard,
    refresh_keyboard,
    settings_menu_keyboard,
    stats_menu_keyboard,
)
from bot.login_flow import begin_login_for_user, handle_login_text, is_login_in_progress
from bot.period_stats import collect_month_stats
from bot.stats_formatters import (
    format_bookings_list,
    format_court_details,
    format_courts_list,
    format_dashboard_stats,
    format_payments_overview,
    format_period_stats,
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

COURT_ACTION_RE = re.compile(
    r"^court:(view|approve|deactivate|confirm:approve|confirm:deactivate):"
    r"(?P<id>[0-9a-fA-F-]{36})$"
)
MONTH_STATS_RE = re.compile(r"^stats:month:(?P<year>\d{4})-(?P<month>\d{2})$")


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


def _get_notifier(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data["notifier"]


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
    notifier = _get_notifier(context)
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


async def show_months_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    await send_message(
        update,
        "🗓 <b>Oylik statistika</b>\n\nOyini tanlang:",
        keyboard=months_menu_keyboard(),
    )


async def show_month_stats(
    update: Update, context: ContextTypes.DEFAULT_TYPE, year: int, month: int
) -> None:
    if not await require_login(update, context):
        return
    api = get_api(context)
    callback = f"stats:month:{year:04d}-{month:02d}"
    await send_message(
        update,
        "⏳ Oylik statistika hisoblanmoqda...",
        keyboard=refresh_keyboard(callback),
    )
    try:
        stats = await collect_month_stats(api, year, month)
        text = format_period_stats(stats)
    except ArenaTopAPIError as exc:
        text = f"API xatolik: {exc}"
    except Exception:
        logger.exception("Month stats failed for %s-%s", year, month)
        text = "Oylik statistikani hisoblashda xatolik yuz berdi."
    await send_message(update, text, keyboard=refresh_keyboard(callback))


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
        items = await api.iter_all_courts()
        # Pending moderation first, then active, then inactive.
        items.sort(
            key=lambda item: (
                0 if not item.get("moderator_approved") else 1,
                0 if item.get("is_active", True) else 1,
                str(item.get("name") or "").lower(),
            )
        )
        text = format_courts_list(items)
        keyboard = courts_list_keyboard(items)
    except ArenaTopAPIError as exc:
        text = f"API xatolik: {exc}"
        keyboard = refresh_keyboard("menu:courts")
    await send_message(update, text, keyboard=keyboard)


async def show_court_details(
    update: Update, context: ContextTypes.DEFAULT_TYPE, court_id: str
) -> None:
    if not await require_login(update, context):
        return
    api = get_api(context)
    try:
        data = await api.get_court(court_id)
        text = format_court_details(data)
        keyboard = court_details_keyboard(
            court_id,
            approved=bool(data.get("moderator_approved")),
            active=bool(data.get("is_active", True)),
        )
    except ArenaTopAPIError as exc:
        text = f"API xatolik: {exc}"
        keyboard = refresh_keyboard("menu:courts")
    await send_message(update, text, keyboard=keyboard)


async def ask_court_action_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
    court_id: str,
) -> None:
    if not await require_login(update, context):
        return
    if action == "approve":
        text = "✅ Bu maydonni tasdiqlaysizmi?"
    else:
        text = "⛔ Bu maydonni nofaol qilasizmi?"
    await send_message(
        update,
        text,
        keyboard=court_confirm_keyboard(action, court_id),
    )


async def confirm_court_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
    court_id: str,
) -> None:
    if not await require_login(update, context):
        return
    api = get_api(context)
    try:
        if action == "approve":
            await api.approve_court(court_id)
            message = "✅ Maydon tasdiqlandi."
        else:
            await api.deactivate_court(court_id)
            message = "⛔ Maydon nofaol qilindi."
    except ArenaTopAPIError as exc:
        await send_message(
            update,
            f"API xatolik: {exc}",
            keyboard=refresh_keyboard(f"court:view:{court_id}"),
        )
        return

    await send_message(update, message)
    await show_court_details(update, context, court_id)


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    api = get_api(context)
    try:
        data = await api.get_me()
        text = format_profile(data)
    except ArenaTopAPIError as exc:
        text = f"API xatolik: {exc}"
    await send_message(update, text, keyboard=settings_menu_keyboard())


async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    auth = get_auth(context)
    user = update.effective_user
    phone = auth.phone_for(user.id) if user else None
    phone_line = format_phone_display(phone) if phone else "—"
    await send_message(
        update,
        "\n".join(
            [
                "👤 <b>Profil / Sozlamalar</b>",
                "",
                f"📱 Telefon: {phone_line}",
                "Kerakli bo'limni tanlang:",
            ]
        ),
        keyboard=settings_menu_keyboard(),
    )


async def show_bot_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_login(update, context):
        return
    settings = get_settings(context)
    notifier = _get_notifier(context)
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
            f"🗓 Kunlik hisobot: har kuni 00:00 ({settings.report_timezone})",
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
            "📊 Statistika — dashboard, oylik hisobot",
            "📋 Bronlar — platforma bronlari",
            "🏟 Maydonlar — ko'rish, tasdiqlash, o'chirish",
            "👤 Profil / Sozlamalar — akkaunt va bot holati",
            "",
            f"Tekshirish intervali: {settings.poll_interval_seconds} soniya",
            f"Kunlik hisobot: 00:00 {settings.report_timezone}",
        ]
    )
    await send_message(update, text, keyboard=settings_menu_keyboard())


async def handle_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    user = update.effective_user
    if not is_admin(user.id if user else None, settings):
        if update.callback_query:
            await update.callback_query.answer("Ruxsat yo'q", show_alert=True)
        elif update.message:
            await update.message.reply_text("Bu botdan foydalanishga ruxsat yo'q.")
        return
    await begin_login_for_user(update, context)


CALLBACK_ROUTES = {
    "menu:main": show_main_menu,
    "menu:payments": show_payments_menu,
    "menu:stats": show_stats_menu,
    "menu:bookings": show_bookings_menu,
    "menu:courts": show_courts,
    "menu:profile": show_settings_menu,
    "menu:settings": show_settings_menu,
    "pay:refunds": show_refunds,
    "pay:withdrawals": show_withdrawals,
    "pay:all": show_all_payments,
    "pay:check": check_payments,
    "stats:dashboard": show_dashboard,
    "stats:users": show_users_stats,
    "stats:today": show_today_stats,
    "stats:months": show_months_menu,
    "book:pending": lambda u, c: show_bookings(u, c, "pending"),
    "book:confirmed": lambda u, c: show_bookings(u, c, "confirmed"),
    "book:completed": lambda u, c: show_bookings(u, c, "completed"),
    "book:cancelled": lambda u, c: show_bookings(u, c, "cancelled"),
    "book:all": lambda u, c: show_bookings(u, c, "all"),
    "set:profile": show_profile,
    "set:status": show_bot_status,
    "set:login": handle_login,
    "set:help": show_help,
}

BUTTON_ROUTES = {
    BTN_PAYMENTS: show_payments_menu,
    BTN_STATS: show_stats_menu,
    BTN_BOOKINGS: show_bookings_menu,
    BTN_COURTS: show_courts,
    BTN_PROFILE_SETTINGS: show_settings_menu,
    BTN_PROFILE: show_settings_menu,
    BTN_SETTINGS: show_settings_menu,
}


async def _handle_dynamic_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> bool:
    month_match = MONTH_STATS_RE.match(data)
    if month_match:
        year = int(month_match.group("year"))
        month = int(month_match.group("month"))
        if not 1 <= month <= 12:
            return False
        await show_month_stats(update, context, year, month)
        return True

    court_match = COURT_ACTION_RE.match(data)
    if not court_match:
        return False

    court_id = court_match.group("id")
    action = court_match.group(1)
    if action == "view":
        await show_court_details(update, context, court_id)
    elif action == "approve":
        await ask_court_action_confirm(update, context, "approve", court_id)
    elif action == "deactivate":
        await ask_court_action_confirm(update, context, "deactivate", court_id)
    elif action.startswith("confirm:"):
        confirmed = action.split(":", 1)[1]
        await confirm_court_action(update, context, confirmed, court_id)
    return True


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
        if not await require_login(update, context):
            return

        if await process_callback_handler(update, context, data):
            return

        handler = CALLBACK_ROUTES.get(data)
        if handler:
            await handler(update, context)
        elif await _handle_dynamic_callback(update, context, data):
            return
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
