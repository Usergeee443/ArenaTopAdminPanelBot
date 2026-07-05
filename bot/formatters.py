from __future__ import annotations

from datetime import datetime
from typing import Any


def _first_value(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def _nested_user(data: dict[str, Any]) -> dict[str, Any] | None:
    user = data.get("user")
    if isinstance(user, dict):
        return user
    customer = data.get("customer")
    if isinstance(customer, dict):
        return customer
    return None


def extract_item_id(item: dict[str, Any]) -> str | None:
    value = _first_value(item, ("id", "uuid", "request_id", "payment_id"))
    if value is None:
        return None
    return str(value)


def extract_amount(item: dict[str, Any]) -> str:
    value = _first_value(
        item,
        (
            "amount",
            "refundable_amount",
            "total_price",
            "sum",
            "total",
            "price",
            "requested_amount",
            "refund_amount",
        ),
    )
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:,.0f} so'm".replace(",", " ")
    return str(value)


def extract_status(item: dict[str, Any]) -> str:
    value = _first_value(item, ("status", "state", "request_status"))
    return str(value) if value is not None else "nomalum"


def extract_refund_status(item: dict[str, Any]) -> str:
    value = _first_value(item, ("refund_status", "status", "state", "request_status"))
    return str(value) if value is not None else "nomalum"


def extract_created_at(item: dict[str, Any]) -> str:
    value = _first_value(
        item,
        ("created_at", "createdAt", "requested_at", "date", "created"),
    )
    if value is None:
        return "—"
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized)
            return dt.strftime("%d.%m.%Y %H:%M")
        except ValueError:
            return value
    return str(value)


def extract_user_label(item: dict[str, Any]) -> str:
    name = _first_value(
        item,
        ("user_name", "admin_name", "full_name", "name", "username"),
    )
    phone = _first_value(item, ("user_phone", "admin_phone", "phone"))
    user_id = _first_value(item, ("user_id", "customer_id", "owner_id"))

    parts: list[str] = []
    if name:
        parts.append(str(name))
    if phone:
        parts.append(str(phone))
    if user_id:
        parts.append(f"ID: {user_id}")

    if parts:
        return " | ".join(parts)

    user = _nested_user(item)
    if user:
        nested_name = _first_value(
            user,
            ("full_name", "name", "username", "phone", "email"),
        )
        nested_id = _first_value(user, ("id", "user_id"))
        if nested_name and nested_id:
            return f"{nested_name} (ID: {nested_id})"
        if nested_name:
            return str(nested_name)
        if nested_id:
            return f"ID: {nested_id}"

    return "—"


def extract_reason(item: dict[str, Any]) -> str | None:
    value = _first_value(
        item,
        ("refund_note", "cancellation_note", "processing_note", "reason", "comment", "description", "note"),
    )
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def extract_payment_ref(item: dict[str, Any]) -> str | None:
    value = _first_value(
        item,
        ("booking_code", "payment_id", "booking_id", "transaction_id", "reference"),
    )
    if value is None:
        return None
    return str(value)


def format_refund_message(item: dict[str, Any]) -> str:
    lines = [
        "🔁 <b>Yangi pul qaytarish so'rovi</b>",
        "",
        f"🆔 So'rov: <code>{extract_item_id(item) or '—'}</code>",
        f"💰 Summa: <b>{extract_amount(item)}</b>",
        f"📌 Holat: <b>{extract_refund_status(item)}</b>",
        f"👤 Foydalanuvchi: {extract_user_label(item)}",
        f"🕒 Sana: {extract_created_at(item)}",
    ]

    payment_ref = extract_payment_ref(item)
    if payment_ref:
        lines.append(f"🧾 Bron kodi: <code>{payment_ref}</code>")

    card = _first_value(item, ("refund_card_number", "card_number"))
    holder = _first_value(item, ("refund_card_holder_name", "card_holder_name"))
    if card:
        lines.append(f"💳 Karta: <code>{card}</code>")
    if holder:
        lines.append(f"👤 Karta egasi: {holder}")

    court = _first_value(item, ("court_name",))
    if court:
        lines.append(f"🏟 Maydon: {court}")

    reason = extract_reason(item)
    if reason:
        lines.append(f"📝 Izoh: {reason}")

    return "\n".join(lines)


def format_withdrawal_message(item: dict[str, Any]) -> str:
    lines = [
        "💸 <b>Yangi pul yechish so'rovi</b>",
        "",
        f"🆔 So'rov: <code>{extract_item_id(item) or '—'}</code>",
        f"💰 Summa: <b>{extract_amount(item)}</b>",
        f"📌 Holat: <b>{extract_status(item)}</b>",
        f"👤 Admin: {extract_user_label(item)}",
        f"🕒 Sana: {extract_created_at(item)}",
    ]

    card = _first_value(item, ("card_number", "card", "account", "wallet"))
    holder = _first_value(item, ("card_holder_name",))
    if card:
        lines.append(f"💳 Karta: <code>{card}</code>")
    if holder:
        lines.append(f"👤 Karta egasi: {holder}")

    reason = extract_reason(item)
    if reason:
        lines.append(f"📝 Izoh: {reason}")

    return "\n".join(lines)


def format_summary(title: str, items: list[dict[str, Any]], formatter) -> str:
    if not items:
        return f"{title}\n\nHozircha so'rovlar yo'q."

    chunks = [title, ""]
    for index, item in enumerate(items[:10], start=1):
        chunks.append(f"{index}. {formatter(item).replace(chr(10), chr(10) + '   ')}")
        chunks.append("")

    if len(items) > 10:
        chunks.append(f"... va yana {len(items) - 10} ta so'rov")

    return "\n".join(chunks).strip()
