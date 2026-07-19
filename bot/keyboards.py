from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from bot.time_utils import month_label, recent_months

# Reply keyboard — asosiy menyu
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["💰 Pul so'rovlari", "📊 Statistika"],
        ["📋 Bronlar", "🏟 Maydonlar"],
        ["👤 Profil / Sozlamalar"],
    ],
    resize_keyboard=True,
)

BTN_PAYMENTS = "💰 Pul so'rovlari"
BTN_STATS = "📊 Statistika"
BTN_BOOKINGS = "📋 Bronlar"
BTN_COURTS = "🏟 Maydonlar"
BTN_PROFILE_SETTINGS = "👤 Profil / Sozlamalar"
# Backward-compatible aliases for older reply keyboards still on client devices
BTN_PROFILE = "👤 Profil"
BTN_SETTINGS = "⚙️ Sozlamalar"

MENU_BUTTONS = {
    BTN_PAYMENTS,
    BTN_STATS,
    BTN_BOOKINGS,
    BTN_COURTS,
    BTN_PROFILE_SETTINGS,
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
            [InlineKeyboardButton("🗓 Oylik statistika", callback_data="stats:months")],
            back_button(),
        ]
    )


def months_menu_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for year, month in recent_months(12):
        label = month_label(year, month)
        row.append(
            InlineKeyboardButton(
                label,
                callback_data=f"stats:month:{year:04d}-{month:02d}",
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(back_button("menu:stats"))
    return InlineKeyboardMarkup(rows)


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
            [InlineKeyboardButton("👤 Profil", callback_data="set:profile")],
            [InlineKeyboardButton("🤖 Bot holati", callback_data="set:status")],
            [InlineKeyboardButton("🔐 Qayta login", callback_data="set:login")],
            [InlineKeyboardButton("❓ Yordam", callback_data="set:help")],
            back_button(),
        ]
    )


def courts_list_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for item in items[:25]:
        court_id = item.get("id")
        if not court_id:
            continue
        name = str(item.get("name") or "Maydon")[:28]
        if not item.get("moderator_approved"):
            prefix = "⏳ "
        elif item.get("is_active", True):
            prefix = "✅ "
        else:
            prefix = "⛔ "
        rows.append(
            [
                InlineKeyboardButton(
                    f"{prefix}{name}",
                    callback_data=f"court:view:{court_id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton("🔄 Yangilash", callback_data="menu:courts")])
    rows.append(back_button())
    return InlineKeyboardMarkup(rows)


def court_details_keyboard(
    court_id: str,
    *,
    approved: bool,
    active: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if not approved:
        rows.append(
            [
                InlineKeyboardButton(
                    "✅ Tasdiqlash",
                    callback_data=f"court:approve:{court_id}",
                )
            ]
        )
    if active:
        rows.append(
            [
                InlineKeyboardButton(
                    "⛔ O'chirish (nofaol)",
                    callback_data=f"court:deactivate:{court_id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton("🔄 Yangilash", callback_data=f"court:view:{court_id}")])
    rows.append(back_button("menu:courts"))
    return InlineKeyboardMarkup(rows)


def court_confirm_keyboard(action: str, court_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Ha",
                    callback_data=f"court:confirm:{action}:{court_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Yo'q",
                    callback_data=f"court:view:{court_id}",
                )
            ],
        ]
    )


def refresh_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔄 Yangilash", callback_data=callback_data)],
            back_button(),
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
