from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

TASHKENT = ZoneInfo("Asia/Tashkent")

UZ_MONTHS = {
    1: "Yanvar",
    2: "Fevral",
    3: "Mart",
    4: "Aprel",
    5: "May",
    6: "Iyun",
    7: "Iyul",
    8: "Avgust",
    9: "Sentabr",
    10: "Oktabr",
    11: "Noyabr",
    12: "Dekabr",
}


def month_label(year: int, month: int) -> str:
    return f"{UZ_MONTHS.get(month, str(month))} {year}"


def recent_months(count: int = 12, *, today: date | None = None) -> list[tuple[int, int]]:
    current = today or datetime.now(TASHKENT).date()
    year, month = current.year, current.month
    months: list[tuple[int, int]] = []
    for _ in range(count):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return months


def previous_local_day(now: datetime | None = None) -> date:
    current = now.astimezone(TASHKENT) if now else datetime.now(TASHKENT)
    return (current - timedelta(days=1)).date()


def day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=TASHKENT)
    end = start + timedelta(days=1)
    return start, end


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=TASHKENT)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=TASHKENT)
    else:
        end = datetime(year, month + 1, 1, tzinfo=TASHKENT)
    return start, end


def parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, time.min, tzinfo=TASHKENT)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            try:
                return datetime.combine(
                    date.fromisoformat(text), time.min, tzinfo=TASHKENT
                )
            except ValueError:
                return None
        normalized = text.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            return None
    else:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(TASHKENT)
    return dt.astimezone(TASHKENT)


def in_period(value: object, start: datetime, end: datetime) -> bool:
    dt = parse_datetime(value)
    if dt is None:
        return False
    return start <= dt < end


def seconds_until_next_local_midnight(now: datetime | None = None) -> float:
    current = now.astimezone(TASHKENT) if now else datetime.now(TASHKENT)
    tomorrow = (current + timedelta(days=1)).date()
    target = datetime.combine(tomorrow, time.min, tzinfo=TASHKENT)
    return max(1.0, (target - current).total_seconds())
