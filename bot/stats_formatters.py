from __future__ import annotations

from typing import Any

from bot.formatters import (
    extract_amount,
    extract_created_at,
    extract_item_id,
    extract_refund_status,
    extract_status,
    extract_user_label,
    format_refund_message,
    format_summary,
    format_withdrawal_message,
)
from bot.period_stats import PeriodStats


def _money(value: Any) -> str:
    if value is None:
        return "0 so'm"
    if isinstance(value, (int, float)):
        return f"{value:,.0f} so'm".replace(",", " ")
    return str(value)


def _int(value: Any) -> str:
    if value is None:
        return "0"
    return f"{int(value):,}".replace(",", " ")


def format_dashboard_stats(data: dict[str, Any]) -> str:
    return "\n".join(
        [
            "📈 <b>ArenaTop Dashboard</b>",
            "",
            "👥 <b>Foydalanuvchilar</b>",
            f"• Mijozlar: <b>{_int(data.get('total_customers'))}</b>",
            f"• VIP mijozlar: <b>{_int(data.get('total_vip_customers'))}</b>",
            f"• Faol adminlar: <b>{_int(data.get('total_active_admins'))}</b>",
            f"• Nofaol: <b>{_int(data.get('total_inactive_users'))}</b>",
            "",
            "🏟 <b>Maydonlar</b>",
            f"• Jami: <b>{_int(data.get('total_courts'))}</b>",
            f"• Faol: <b>{_int(data.get('active_courts'))}</b>",
            f"• Kutilmoqda: <b>{_int(data.get('pending_courts'))}</b>",
            "",
            "📋 <b>Bronlar</b>",
            f"• Jami: <b>{_int(data.get('total_bookings'))}</b>",
            f"• Kutilmoqda: <b>{_int(data.get('bookings_pending'))}</b>",
            f"• Tasdiqlangan: <b>{_int(data.get('bookings_confirmed'))}</b>",
            f"• Tugallangan: <b>{_int(data.get('bookings_completed'))}</b>",
            f"• Bekor: <b>{_int(data.get('bookings_cancelled'))}</b>",
            f"• Qaytarilgan: <b>{_int(data.get('bookings_refunded'))}</b>",
            "",
            "💳 <b>To'lovlar</b>",
            f"• Kutilmoqda: <b>{_int(data.get('payments_pending'))}</b>",
            f"• Tugallangan: <b>{_int(data.get('payments_completed'))}</b>",
            f"• Summa: <b>{_money(data.get('payments_completed_amount'))}</b>",
            f"• Xato: <b>{_int(data.get('payments_failed'))}</b>",
            "",
            "🔁 <b>Qaytarishlar</b>",
            f"• Kutilmoqda: <b>{_int(data.get('refunds_pending'))}</b>",
            f"• Bajarilgan: <b>{_int(data.get('refunds_processed'))}</b>",
            f"• Rad etilgan: <b>{_int(data.get('refunds_rejected'))}</b>",
            "",
            "💸 <b>Yechishlar</b>",
            f"• Kutilmoqda: <b>{_int(data.get('total_withdrawals_pending'))}</b> "
            f"({_money(data.get('total_withdrawals_pending_amount'))})",
            f"• Bajarilgan: <b>{_int(data.get('total_withdrawals_completed'))}</b> "
            f"({_money(data.get('total_withdrawals_completed_amount'))})",
            "",
            f"⭐ Sharhlar: <b>{_int(data.get('total_reviews'))}</b>",
        ]
    )


def format_users_summary(data: dict[str, Any]) -> str:
    return "\n".join(
        [
            "👥 <b>Foydalanuvchilar statistikasi</b>",
            "",
            f"📊 Jami: <b>{_int(data.get('total'))}</b>",
            f"✅ Faol: <b>{_int(data.get('active'))}</b>",
            f"⛔ Nofaol: <b>{_int(data.get('inactive'))}</b>",
            "",
            "🛍 <b>Mijozlar</b>",
            f"• Jami: {_int(data.get('clients'))}",
            f"• Faol: {_int(data.get('clients_active'))}",
            f"• Nofaol: {_int(data.get('clients_inactive'))}",
            "",
            "🏢 <b>Biznes</b>",
            f"• Jami: {_int(data.get('business'))}",
            f"• Faol: {_int(data.get('business_active'))}",
            f"• Nofaol: {_int(data.get('business_inactive'))}",
            "",
            "🛡 <b>Platforma</b>",
            f"• Jami: {_int(data.get('platform'))}",
            f"• Faol: {_int(data.get('platform_active'))}",
            f"• Nofaol: {_int(data.get('platform_inactive'))}",
        ]
    )


def format_today_stats(data: dict[str, Any]) -> str:
    lines = [
        "📅 <b>Bugungi statistika</b>",
        "",
        f"💰 Bugungi daromad: <b>{_money(data.get('today_total_income'))}</b>",
        f"   • Onlayn: {_money(data.get('today_online_income'))}",
        f"   • Naqd: {_money(data.get('today_offline_income'))}",
        "",
        f"📋 Jami bronlar: <b>{_int(data.get('total_bookings'))}</b>",
        f"✅ Tugallangan: <b>{_int(data.get('completed_bookings'))}</b>",
        f"❌ Bekor: <b>{_int(data.get('cancelled_bookings'))}</b>",
        "",
        f"💵 Jami daromad: <b>{_money(data.get('total_income'))}</b>",
        f"💸 Yechilgan: <b>{_money(data.get('total_withdrawn'))}</b>",
        f"🏦 Balans: <b>{_money(data.get('current_balance'))}</b>",
    ]
    if data.get("period_start"):
        lines.extend(
            [
                "",
                f"📆 Davr: {data.get('period_start')} — {data.get('period_end')}",
                f"📋 Bronlar: {_int(data.get('period_bookings'))}",
                f"💰 Daromad: {_money(data.get('period_income'))}",
            ]
        )
    return "\n".join(lines)


def format_profile(data: dict[str, Any]) -> str:
    role = data.get("role") or "—"
    if isinstance(data.get("role_ref"), dict):
        role = data["role_ref"].get("name") or data["role_ref"].get("slug") or role

    perms = data.get("permissions") or []
    perm_text = f"{len(perms)} ta ruxsat" if perms else "—"

    return "\n".join(
        [
            "👤 <b>Profil</b>",
            "",
            f"📛 Ism: <b>{data.get('name', '—')}</b>",
            f"📱 Telefon: <code>{data.get('phone_number', '—')}</code>",
            f"🎭 Rol: <b>{role}</b>",
            f"🔑 Ruxsatlar: {perm_text}",
            f"✅ Holat: {'Faol' if data.get('is_active', True) else 'Nofaol'}",
            f"🆔 ID: <code>{data.get('id', '—')}</code>",
        ]
    )


def format_booking_item(item: dict[str, Any]) -> str:
    court = item.get("court_name") or "—"
    code = item.get("booking_code") or extract_item_id(item) or "—"
    date = item.get("date") or "—"
    time = item.get("start_time") or "—"
    status = extract_status(item)
    price = extract_amount(item)
    user = extract_user_label(item)
    return (
        f"🧾 <code>{code}</code> | {date} {time}\n"
        f"   🏟 {court} | 💰 {price} | 📌 {status}\n"
        f"   👤 {user}"
    )


def format_bookings_list(items: list[dict[str, Any]], title: str) -> str:
    if not items:
        return f"{title}\n\nHozircha bronlar yo'q."

    lines = [title, ""]
    for index, item in enumerate(items[:10], start=1):
        lines.append(f"{index}. {format_booking_item(item)}")

    if len(items) > 10:
        lines.append(f"\n... va yana {len(items) - 10} ta bron")
    return "\n".join(lines)


def format_court_item(item: dict[str, Any]) -> str:
    name = item.get("name") or "—"
    price = _money(item.get("price_per_hour"))
    rating = item.get("rating", 0)
    location = item.get("location_name") or "—"
    active = "✅" if item.get("is_active", True) else "⛔"
    approved = "✅" if item.get("moderator_approved") else "⏳"
    return (
        f"{active} <b>{name}</b>\n"
        f"   📍 {location} | 💰 {price}/soat\n"
        f"   ⭐ {rating} | Tasdiq: {approved}"
    )


def format_courts_list(items: list[dict[str, Any]]) -> str:
    if not items:
        return "🏟 <b>Maydonlar</b>\n\nMaydonlar topilmadi."

    pending = sum(1 for item in items if not item.get("moderator_approved"))
    active = sum(1 for item in items if item.get("is_active", True))
    lines = [
        "🏟 <b>Maydonlar</b>",
        f"Jami: <b>{len(items)}</b> | Kutilmoqda: <b>{pending}</b> | Faol: <b>{active}</b>",
        "",
        "Maydonni tanlang 👇",
    ]
    return "\n".join(lines)


def format_court_details(data: dict[str, Any]) -> str:
    category = data.get("category")
    if isinstance(category, dict):
        category_name = category.get("name") or "—"
    else:
        category_name = "—"

    approved = "✅ Tasdiqlangan" if data.get("moderator_approved") else "⏳ Kutilmoqda"
    active = "✅ Faol" if data.get("is_active", True) else "⛔ Nofaol"
    created = extract_created_at(data)

    return "\n".join(
        [
            f"🏟 <b>{data.get('name', 'Maydon')}</b>",
            "",
            f"📍 Manzil: {data.get('location_name') or '—'}",
            f"🏷 Kategoriya: {category_name}",
            f"💰 Narx: {_money(data.get('price_per_hour'))}/soat",
            f"🕒 Ish vaqti: {data.get('work_time') or '—'}",
            f"⭐ Reyting: {data.get('rating', 0)} ({_int(data.get('rating_count'))} sharh)",
            f"📌 Holat: {active}",
            f"🛡 Moderatsiya: {approved}",
            f"🗓 Yaratilgan: {created}",
            f"🆔 <code>{data.get('id', '—')}</code>",
        ]
    )


def format_period_stats(stats: PeriodStats) -> str:
    return "\n".join(
        [
            f"📊 <b>{stats.label} statistikasi</b>",
            "",
            f"👥 Yangi foydalanuvchilar: <b>{_int(stats.new_users)}</b>",
            f"🏟 Yangi maydonlar: <b>{_int(stats.new_courts)}</b>",
            f"📋 Jami bronlar: <b>{_int(stats.total_bookings)}</b>",
            f"💳 To'langan bronlar: <b>{_int(stats.paid_bookings)}</b>",
            f"💰 Daromad: <b>{_money(stats.revenue)}</b>",
            f"⭐ Yangi sharhlar: <b>{_int(stats.new_reviews)}</b>",
        ]
    )


def format_refunds_list(items: list[dict[str, Any]], title: str) -> str:
    return format_summary(title, items, format_refund_message)


def format_withdrawals_list(items: list[dict[str, Any]], title: str) -> str:
    return format_summary(title, items, format_withdrawal_message)


def format_payments_overview(
    refunds: list[dict[str, Any]], withdrawals: list[dict[str, Any]]
) -> str:
    pending_refunds = sum(
        1 for item in refunds if extract_refund_status(item).lower() == "pending"
    )
    pending_withdrawals = sum(
        1 for item in withdrawals if extract_status(item).lower() == "pending"
    )
    return "\n".join(
        [
            "💰 <b>Pul so'rovlari</b>",
            "",
            f"🔁 Qaytarishlar: <b>{len(refunds)}</b> (kutilmoqda: {pending_refunds})",
            f"💸 Yechishlar: <b>{len(withdrawals)}</b> (kutilmoqda: {pending_withdrawals})",
            "",
            "Batafsil ko'rish uchun tugmalardan foydalaning.",
        ]
    )
