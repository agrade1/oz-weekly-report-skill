# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "holidays>=0.82,<1",
#   "pydantic>=2.11,<3",
# ]
# ///

from __future__ import annotations

import sys
from datetime import date, datetime, time, timedelta
from typing import ClassVar
from zoneinfo import ZoneInfo

import holidays
from pydantic import BaseModel, ConfigDict, Field


class WindowInput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    run_at: datetime
    last_successful_report_at: datetime | None
    timezone: str
    scheduled_run: bool = False
    extra_holidays: tuple[date, ...] = Field(default_factory=tuple)


class WindowResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    comparison_start: datetime
    start: datetime
    end: datetime
    replay: bool
    should_run: bool
    first_business_day: date


def korean_holidays(years: set[int], extra: tuple[date, ...]) -> set[date]:
    return set(holidays.KR(years=years).keys()) | set(extra)


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def first_business_day(monday: date, holiday_dates: set[date]) -> date:
    for offset in range(7):
        candidate = monday + timedelta(days=offset)
        if candidate.weekday() < 5 and candidate not in holiday_dates:
            return candidate
    raise ValueError("business day not found")


def cutoff_for_week(monday: date, timezone: ZoneInfo, holiday_dates: set[date]) -> datetime:
    business_day = first_business_day(monday, holiday_dates)
    return datetime.combine(business_day, time(10, 30), tzinfo=timezone)


def previous_cutoff(cutoff: datetime, timezone: ZoneInfo, holiday_dates: set[date]) -> datetime:
    previous_monday = monday_of(cutoff.astimezone(timezone).date()) - timedelta(days=7)
    return cutoff_for_week(previous_monday, timezone, holiday_dates)


def calculate_window(payload: WindowInput) -> WindowResult:
    timezone = ZoneInfo(payload.timezone)
    local_run_at = payload.run_at.astimezone(timezone)
    years = {local_run_at.year - 1, local_run_at.year, local_run_at.year + 1}
    holiday_dates = korean_holidays(years, payload.extra_holidays)
    current_monday = monday_of(local_run_at.date())
    current_first_day = first_business_day(current_monday, holiday_dates)
    current_cutoff = cutoff_for_week(current_monday, timezone, holiday_dates)
    end = previous_cutoff(current_cutoff, timezone, holiday_dates) if current_cutoff > local_run_at else current_cutoff
    saved = payload.last_successful_report_at
    replay = saved is not None and saved.astimezone(timezone) >= end
    if saved is None or replay:
        start = previous_cutoff(end, timezone, holiday_dates)
    else:
        start = saved.astimezone(timezone)
    should_run = not payload.scheduled_run or (
        local_run_at.date() == current_first_day and local_run_at >= current_cutoff
    )
    return WindowResult(
        comparison_start=previous_cutoff(start, timezone, holiday_dates),
        start=start,
        end=end,
        replay=replay,
        should_run=should_run,
        first_business_day=current_first_day,
    )


def main() -> None:
    payload = WindowInput.model_validate_json(sys.stdin.read())
    _ = sys.stdout.write(calculate_window(payload).model_dump_json())
    _ = sys.stdout.write("\n")


if __name__ == "__main__":
    main()
