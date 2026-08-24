# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pydantic>=2.11,<3",
# ]
# ///
# ─── How to run ───
# printf '%s' '{"prior_unique_count":3,"current_daily_counts":[{"date":"2026-08-07","unique_count":35}],"total_unique_count":38}' | uv run detect-learning-survey.py

from __future__ import annotations

import sys
from datetime import date
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt

DailyCounts = Annotated[tuple["DailyCount", ...], Field(min_length=1)]


class DailyCount(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    date: date
    unique_count: PositiveInt


class DetectionInput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    prior_unique_count: NonNegativeInt
    current_daily_counts: DailyCounts
    total_unique_count: PositiveInt


class DetectionResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    is_new: bool
    survey_date: date | None
    reason: Literal[
        "first_response", "pre_open_response_exception", "late_response"
    ]


def detect(payload: DetectionInput) -> DetectionResult:
    ordered = tuple(sorted(payload.current_daily_counts, key=lambda item: item.date))
    if payload.prior_unique_count == 0:
        return DetectionResult(
            is_new=True,
            survey_date=ordered[0].date,
            reason="first_response",
        )

    current_unique_count = sum(item.unique_count for item in ordered)
    response_wave_dates = tuple(item.date for item in ordered if item.unique_count >= 5)
    is_pre_open_response_exception = (
        payload.prior_unique_count <= 3
        and current_unique_count >= 5
        and bool(response_wave_dates)
        and current_unique_count * 10 >= payload.total_unique_count * 7
    )
    if is_pre_open_response_exception:
        return DetectionResult(
            is_new=True,
            survey_date=response_wave_dates[0],
            reason="pre_open_response_exception",
        )

    return DetectionResult(
        is_new=False,
        survey_date=None,
        reason="late_response",
    )


def main() -> None:
    payload = DetectionInput.model_validate_json(sys.stdin.read())
    _ = sys.stdout.write(detect(payload).model_dump_json())
    _ = sys.stdout.write("\n")


if __name__ == "__main__":
    main()
