from __future__ import annotations

import logging
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from bot.api_client import ArenaTopAPIError
from bot.formatters import extract_refund_status, extract_status
from bot.keyboards import (
    MAIN_MENU,
    cancel_process_keyboard,
    refund_actions_keyboard,
    refresh_keyboard,
    withdrawal_actions_keyboard,
)
from bot.ui_utils import get_api, send_message

logger = logging.getLogger(__name__)

PENDING_KEY = "pending_process"


def is_pending_refund(item: dict[str, Any]) -> bool:
    return extract_refund_status(item).lower() in {"pending", "requested"}


def is_pending_withdrawal(item: dict[str, Any]) -> bool:
    return extract_status(item).lower() == "pending"


async def send_refund_items(
    update: Update, context: ContextTypes.DEFAULT_TYPE, items: list[dict]
) -> None:
    from bot.formatters import format_refund_message

    pending = [item for item in items if is_pending_refund(item)]
    header = (
        f"🔁 <b>Pul qaytarish so'rovlari</b>\n\n"
        f"Jami: {len(items)} | Kutilmoqda: {len(pending)}"
    )
    await send_message(update, header)

    chat_id = update.effective_chat.id if update.effective_chat else None
    if not chat_id:
        return

    if not pending:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Kutilayotgan qaytarish so'rovlari yo'q.",
            parse_mode="HTML",
        )
        return

    for item in pending[:15]:
        item_id = item.get("id")
        if not item_id:
            continue
        await context.bot.send_message(
            chat_id=chat_id,
            text=format_refund_message(item),
            parse_mode="HTML",
            reply_markup=refund_actions_keyboard(str(item_id)),
        )

    await context.bot.send_message(
        chat_id=chat_id,
        text="👇 Amal bajarish uchun tugmani bosing",
        reply_markup=refresh_keyboard("pay:refunds"),
    )


async def send_withdrawal_items(
    update: Update, context: ContextTypes.DEFAULT_TYPE, items: list[dict]
) -> None:
    from bot.formatters import format_withdrawal_message

    pending = [item for item in items if is_pending_withdrawal(item)]
    header = (
        f"💸 <b>Pul yechish so'rovlari</b>\n\n"
        f"Jami: {len(items)} | Kutilmoqda: {len(pending)}"
    )
    await send_message(update, header)

    chat_id = update.effective_chat.id if update.effective_chat else None
    if not chat_id:
        return

    if not pending:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Kutilayotgan yechish so'rovlari yo'q.",
            parse_mode="HTML",
        )
        return

    for item in pending[:15]:
        item_id = item.get("id")
        if not item_id:
            continue
        await context.bot.send_message(
            chat_id=chat_id,
            text=format_withdrawal_message(item),
            parse_mode="HTML",
            reply_markup=withdrawal_actions_keyboard(str(item_id)),
        )

    await context.bot.send_message(
        chat_id=chat_id,
        text="👇 Amal bajarish uchun tugmani bosing",
        reply_markup=refresh_keyboard("pay:withdrawals"),
    )


def set_pending(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    kind: str,
    item_id: str,
    status: str,
    needs_receipt: bool,
) -> None:
    context.user_data[PENDING_KEY] = {
        "kind": kind,
        "id": item_id,
        "status": status,
        "needs_receipt": needs_receipt,
    }


def clear_pending(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(PENDING_KEY, None)


def has_pending(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return PENDING_KEY in context.user_data


async def ask_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_message(
        update,
        "📎 <b>Chek yuboring</b>\n\n"
        "To'lov chekini rasm (photo) yoki PDF hujjat sifatida yuboring.\n"
        "Chek yuklangandan keyin so'rov holati yangilanadi.",
        keyboard=cancel_process_keyboard(),
    )


async def start_refund_approve(
    update: Update, context: ContextTypes.DEFAULT_TYPE, booking_id: str
) -> None:
    set_pending(
        context,
        kind="refund",
        item_id=booking_id,
        status="processed",
        needs_receipt=True,
    )
    await ask_receipt(update, context)


async def start_withdrawal_approve(
    update: Update, context: ContextTypes.DEFAULT_TYPE, withdrawal_id: str
) -> None:
    set_pending(
        context,
        kind="withdrawal",
        item_id=withdrawal_id,
        status="completed",
        needs_receipt=True,
    )
    await ask_receipt(update, context)


async def reject_refund(
    update: Update, context: ContextTypes.DEFAULT_TYPE, booking_id: str
) -> None:
    api = get_api(context)
    try:
        await api.process_refund_request(booking_id, status="rejected")
        await send_message(
            update,
            f"❌ Qaytarish so'rovi rad etildi.\n🆔 <code>{booking_id}</code>",
            reply_keyboard=MAIN_MENU,
        )
    except ArenaTopAPIError as exc:
        await send_message(update, f"Xatolik: {exc}", reply_keyboard=MAIN_MENU)


async def reject_withdrawal(
    update: Update, context: ContextTypes.DEFAULT_TYPE, withdrawal_id: str
) -> None:
    api = get_api(context)
    try:
        await api.process_withdrawal(withdrawal_id, status="failed")
        await send_message(
            update,
            f"❌ Yechish so'rovi rad etildi.\n🆔 <code>{withdrawal_id}</code>",
            reply_keyboard=MAIN_MENU,
        )
    except ArenaTopAPIError as exc:
        await send_message(update, f"Xatolik: {exc}", reply_keyboard=MAIN_MENU)


async def download_telegram_file(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> tuple[bytes, str, str]:
    message = update.message
    if not message:
        raise ValueError("Xabar topilmadi")

    if message.photo:
        tg_file = await context.bot.get_file(message.photo[-1].file_id)
        return (
            bytes(await tg_file.download_as_bytearray()),
            "receipt.jpg",
            "image/jpeg",
        )

    if message.document:
        tg_file = await context.bot.get_file(message.document.file_id)
        filename = message.document.file_name or "receipt.pdf"
        mime = message.document.mime_type or "application/octet-stream"
        return bytes(await tg_file.download_as_bytearray()), filename, mime

    raise ValueError("Rasm yoki hujjat yuboring")


async def submit_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pending = context.user_data.get(PENDING_KEY)
    if not pending or not pending.get("needs_receipt"):
        return

    if update.message:
        await update.message.reply_text("Chek yuklanmoqda...")

    try:
        file_bytes, filename, content_type = await download_telegram_file(
            update, context
        )
    except ValueError as exc:
        if update.message:
            await update.message.reply_text(str(exc))
        return

    api = get_api(context)
    kind = pending["kind"]
    item_id = pending["id"]
    status = pending["status"]

    try:
        if kind == "refund":
            result = await api.process_refund_request(
                item_id,
                status=status,
                receipt_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
            )
            new_status = result.get("refund_status") or status
            success = (
                f"✅ <b>Pul qaytarildi!</b>\n\n"
                f"🆔 So'rov: <code>{item_id}</code>\n"
                f"📌 Yangi holat: <b>{new_status}</b>"
            )
            if result.get("refund_receipt_url"):
                success += f"\n🧾 Chek: {result['refund_receipt_url']}"
        else:
            result = await api.process_withdrawal(
                item_id,
                status=status,
                receipt_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
            )
            new_status = result.get("status") or status
            success = (
                f"✅ <b>To'lov bajarildi!</b>\n\n"
                f"🆔 So'rov: <code>{item_id}</code>\n"
                f"📌 Yangi holat: <b>{new_status}</b>"
            )
            if result.get("receipt_url"):
                success += f"\n🧾 Chek: {result['receipt_url']}"
    except ArenaTopAPIError as exc:
        if update.message:
            await update.message.reply_text(f"API xatolik: {exc}", reply_markup=MAIN_MENU)
        return
    finally:
        clear_pending(context)

    if update.message:
        await update.message.reply_text(success, parse_mode="HTML", reply_markup=MAIN_MENU)


async def cancel_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_pending(context)
    await send_message(
        update,
        "Bekor qilindi.",
        reply_keyboard=MAIN_MENU,
    )


async def process_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> bool:
    if data == "process:cancel":
        await cancel_process(update, context)
        return True

    if data.startswith("refund:done:"):
        await start_refund_approve(update, context, data.split(":", 2)[2])
        return True

    if data.startswith("refund:reject:"):
        await reject_refund(update, context, data.split(":", 2)[2])
        return True

    if data.startswith("wd:done:"):
        await start_withdrawal_approve(update, context, data.split(":", 2)[2])
        return True

    if data.startswith("wd:reject:"):
        await reject_withdrawal(update, context, data.split(":", 2)[2])
        return True

    return False
