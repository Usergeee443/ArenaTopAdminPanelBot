from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

# Reply keyboard — asosiy menyu
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["💰 Pul so'rovlari", "📊 Statistika"],
        ["📋 Bronlar", "🏟 Maydonlar"],
        ["👤 Profil", "⚙️ Sozlamalar"],
    ],
    resize_keyboard=True,
)

BTN_PAYMENTS = "💰 Pul so'rovlari"
BTN_STATS = "📊 Statistika"
BTN_BOOKINGS = "📋 Bronlar"
BTN_COURTS = "🏟 Maydonlar"
BTN_PROFILE = "👤 Profil"
BTN_SETTINGS = "⚙️ Sozlamalar"

MENU_BUTTONS = {
    BTN_PAYMENTS,
    BTN_STATS,
    BTN_BOOKINGS,
    BTN_COURTS,
    BTN_PROFILE,
    BTN_SETTINGS,
}


def back_button(callback_data: str = "menu:main") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton("◀️ Orqaga", callback_data=callback_data)]


def payments_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔁 Qaytarishlar", callback_data="pay:refunds")],
            [InlineKeyboardButton("💸 Yechishlar", callback_data="pay:withdrawals")],
            [
                InlineKeyboardButton("📋 Barchasi", callback_data="pay:all"),
                InlineKeyboardButton("🔄 Tekshirish", callback_data="pay:check"),
            ],
            back_button(),
        ]
    )


def stats_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📈 Dashboard", callback_data="stats:dashboard")],
            [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="stats:users")],
            [InlineKeyboardButton("📅 Bugungi daromad", callback_data="stats:today")],
            back_button(),
        ]
    )


def bookings_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏳ Kutilmoqda", callback_data="book:pending"),
                InlineKeyboardButton("✅ Tasdiq", callback_data="book:confirmed"),
            ],
            [
                InlineKeyboardButton("🏁 Tugallangan", callback_data="book:completed"),
                InlineKeyboardButton("❌ Bekor", callback_data="book:cancelled"),
            ],
            [InlineKeyboardButton("📋 Barchasi", callback_data="book:all")],
            back_button(),
        ]
    )


def settings_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🤖 Bot holati", callback_data="set:status")],
            [InlineKeyboardButton("🔐 Qayta login", callback_data="set:login")],
            [InlineKeyboardButton("❓ Yordam", callback_data="set:help")],
            back_button(),
        ]
    )


def refresh_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔄 Yangilash", callback_data=callback_data)],
            *back_button(),
        ]
    )


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
