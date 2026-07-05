from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def refund_actions_keyboard(booking_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Pul qaytarildi",
                    callback_data=f"refund:done:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Rad etish",
                    callback_data=f"refund:reject:{booking_id}",
                )
            ],
        ]
    )


def withdrawal_actions_keyboard(withdrawal_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ To'lov qilindi",
                    callback_data=f"wd:done:{withdrawal_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Rad etish",
                    callback_data=f"wd:reject:{withdrawal_id}",
                )
            ],
        ]
    )


def cancel_process_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Bekor qilish", callback_data="process:cancel")]]
    )
