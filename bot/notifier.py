from __future__ import annotations

import asyncio
import logging

from telegram.ext import Application

from bot.api_client import ArenaTopAPIError, ArenaTopClient
from bot.config import Settings
from bot.formatters import (
    extract_item_id,
    format_refund_message,
    format_withdrawal_message,
    format_summary,
)
from bot.keyboards import refund_actions_keyboard, withdrawal_actions_keyboard
from bot.process_flow import is_pending_refund, is_pending_withdrawal
from bot.storage import SeenStorage

logger = logging.getLogger(__name__)


class PaymentNotifier:
    def __init__(
        self,
        settings: Settings,
        api_client: ArenaTopClient,
        storage: SeenStorage,
    ) -> None:
        self._settings = settings
        self._api = api_client
        self._storage = storage
        self._started = False

    def storage_counts(self) -> dict[str, int]:
        return self._storage.counts()

    async def seed_existing_requests(self) -> None:
        refunds = await self._api.get_refund_requests(self._settings.refund_statuses)
        withdrawals = await self._api.get_withdrawal_requests(
            self._settings.withdrawal_statuses
        )

        refund_ids = [
            item_id
            for item in refunds
            if (item_id := extract_item_id(item)) is not None
        ]
        withdrawal_ids = [
            item_id
            for item in withdrawals
            if (item_id := extract_item_id(item)) is not None
        ]

        self._storage.mark_many_seen("refunds", refund_ids)
        self._storage.mark_many_seen("withdrawals", withdrawal_ids)
        self._started = True

        logger.info(
            "Seeded storage: %s refunds, %s withdrawals",
            len(refund_ids),
            len(withdrawal_ids),
        )

    async def _notify_admins(
        self,
        application: Application,
        text: str,
        reply_markup=None,
    ) -> None:
        auth = application.bot_data.get("auth")
        recipients = set(self._settings.admin_telegram_ids)
        if auth is not None:
            recipients.update(auth.logged_in_telegram_ids())

        for admin_id in recipients:
            try:
                await application.bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=reply_markup,
                )
            except Exception:
                logger.exception("Failed to notify admin %s", admin_id)

    async def check_and_notify(self, application: Application) -> dict[str, int]:
        sent = {"refunds": 0, "withdrawals": 0}

        refunds = await self._api.get_refund_requests(self._settings.refund_statuses)
        for item in refunds:
            item_id = extract_item_id(item)
            if not item_id or self._storage.is_seen("refunds", item_id):
                continue
            if self._started:
                keyboard = None
                if is_pending_refund(item):
                    keyboard = refund_actions_keyboard(item_id)
                await self._notify_admins(
                    application,
                    format_refund_message(item),
                    reply_markup=keyboard,
                )
                sent["refunds"] += 1
            self._storage.mark_seen("refunds", item_id)

        withdrawals = await self._api.get_withdrawal_requests(
            self._settings.withdrawal_statuses
        )
        for item in withdrawals:
            item_id = extract_item_id(item)
            if not item_id or self._storage.is_seen("withdrawals", item_id):
                continue
            if self._started:
                keyboard = None
                if is_pending_withdrawal(item):
                    keyboard = withdrawal_actions_keyboard(item_id)
                await self._notify_admins(
                    application,
                    format_withdrawal_message(item),
                    reply_markup=keyboard,
                )
                sent["withdrawals"] += 1
            self._storage.mark_seen("withdrawals", item_id)

        return sent

    async def get_pending_summary(self) -> tuple[str, str]:
        refunds = await self._api.get_refund_requests(self._settings.refund_statuses)
        withdrawals = await self._api.get_withdrawal_requests(
            self._settings.withdrawal_statuses
        )

        refund_text = format_summary(
            "🔁 <b>Kutilayotgan pul qaytarishlar</b>",
            refunds,
            format_refund_message,
        )
        withdrawal_text = format_summary(
            "💸 <b>Kutilayotgan pul yechish so'rovlari</b>",
            withdrawals,
            format_withdrawal_message,
        )
        return refund_text, withdrawal_text

    async def run_polling_loop(self, application: Application) -> None:
        while True:
            try:
                result = await self.check_and_notify(application)
                if result["refunds"] or result["withdrawals"]:
                    logger.info("Sent notifications: %s", result)
            except ArenaTopAPIError as exc:
                logger.error("API error during polling: %s", exc)
                if exc.status_code == 401:
                    auth = application.bot_data.get("auth")
                    if auth is not None:
                        await auth.invalidate()
                        application.bot_data["notifier_started"] = False
                        from bot.login_flow import begin_login

                        await begin_login(application)
            except Exception:
                logger.exception("Unexpected polling error")

            await asyncio.sleep(self._settings.poll_interval_seconds)
