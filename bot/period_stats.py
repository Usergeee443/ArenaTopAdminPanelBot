from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from bot.api_client import ArenaTopClient
from bot.time_utils import (
    day_bounds,
    in_period,
    month_bounds,
    month_label,
)


@dataclass(frozen=True)
class PeriodStats:
    label: str
    start: date
    end: date
    new_users: int
    new_courts: int
    total_bookings: int
    paid_bookings: int
    revenue: int
    new_reviews: int


def _booking_revenue(item: dict[str, Any]) -> int:
    online = item.get("amount_paid_online") or 0
    venue = item.get("venue_amount_confirmed") or 0
    try:
        total = int(online) + int(venue)
    except (TypeError, ValueError):
        total = 0
    if total > 0:
        return total
    if item.get("is_fully_paid"):
        try:
            return int(item.get("total_price") or 0)
        except (TypeError, ValueError):
            return 0
    return 0


def _is_paid_booking(item: dict[str, Any]) -> bool:
    if item.get("is_fully_paid"):
        return True
    return _booking_revenue(item) > 0


async def _count_new_courts(
    api: ArenaTopClient,
    courts: list[dict[str, Any]],
    start: datetime,
    end: datetime,
) -> int:
    count = 0
    missing_ids: list[str] = []
    for court in courts:
        created = court.get("created_at")
        if created is None:
            court_id = court.get("id")
            if court_id:
                missing_ids.append(str(court_id))
            continue
        if in_period(created, start, end):
            count += 1

    semaphore = asyncio.Semaphore(5)

    async def fetch_one(court_id: str) -> bool:
        async with semaphore:
            try:
                detail = await api.get_court(court_id)
            except Exception:
                return False
            return in_period(detail.get("created_at"), start, end)

    if missing_ids:
        results = await asyncio.gather(*(fetch_one(cid) for cid in missing_ids))
        count += sum(1 for matched in results if matched)
    return count


async def _count_new_reviews(
    api: ArenaTopClient,
    courts: list[dict[str, Any]],
    start: datetime,
    end: datetime,
) -> int:
    semaphore = asyncio.Semaphore(5)

    async def count_for_court(court_id: str) -> int:
        async with semaphore:
            matched = 0
            offset = 0
            page_size = 100
            while offset <= 300:
                try:
                    page = await api.get_court_reviews(
                        court_id, limit=page_size, offset=offset
                    )
                except Exception:
                    return matched
                if not page:
                    break
                for review in page:
                    if in_period(review.get("created_at"), start, end):
                        matched += 1
                if len(page) < page_size:
                    break
                offset += page_size
            return matched

    court_ids = [str(c["id"]) for c in courts if c.get("id")]
    if not court_ids:
        return 0
    results = await asyncio.gather(*(count_for_court(cid) for cid in court_ids))
    return sum(results)


async def collect_period_stats(
    api: ArenaTopClient,
    *,
    label: str,
    start: datetime,
    end: datetime,
) -> PeriodStats:
    users, courts, bookings = await asyncio.gather(
        api.iter_all_users(),
        api.iter_all_courts(),
        api.iter_all_bookings(from_date=start.date().isoformat()),
    )

    new_users = sum(1 for user in users if in_period(user.get("created_at"), start, end))
    new_courts = await _count_new_courts(api, courts, start, end)

    period_bookings = [
        booking
        for booking in bookings
        if in_period(booking.get("date") or booking.get("created_at"), start, end)
    ]
    paid_bookings = [b for b in period_bookings if _is_paid_booking(b)]
    revenue = sum(_booking_revenue(b) for b in paid_bookings)
    new_reviews = await _count_new_reviews(api, courts, start, end)

    return PeriodStats(
        label=label,
        start=start.date(),
        end=(end - timedelta(seconds=1)).date(),
        new_users=new_users,
        new_courts=new_courts,
        total_bookings=len(period_bookings),
        paid_bookings=len(paid_bookings),
        revenue=revenue,
        new_reviews=new_reviews,
    )


async def collect_day_stats(api: ArenaTopClient, day: date) -> PeriodStats:
    start, end = day_bounds(day)
    return await collect_period_stats(
        api,
        label=day.strftime("%d.%m.%Y"),
        start=start,
        end=end,
    )


async def collect_month_stats(
    api: ArenaTopClient, year: int, month: int
) -> PeriodStats:
    start, end = month_bounds(year, month)
    return await collect_period_stats(
        api,
        label=month_label(year, month),
        start=start,
        end=end,
    )
