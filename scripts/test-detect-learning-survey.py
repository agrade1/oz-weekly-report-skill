# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pydantic>=2.11,<3",
#   "pytest>=8.4,<9",
# ]
# ///
# ─── How to run ───
# uv run test-detect-learning-survey.py

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import ClassVar, Final, Literal

import pytest
from pydantic import BaseModel, ConfigDict

DETECTOR: Final = Path(__file__).with_name("detect-learning-survey.py")


class DetectionResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    is_new: bool
    survey_date: date | None
    reason: Literal[
        "first_response", "pre_open_response_exception", "late_response"
    ]


def run_detector(payload: dict[str, int | list[dict[str, int | str]]]) -> DetectionResult:
    completed = subprocess.run(
        [sys.executable, str(DETECTOR)],
        input=json.dumps(payload),
        check=True,
        capture_output=True,
        text=True,
    )
    return DetectionResult.model_validate_json(completed.stdout)


def test_corrects_one_ui_design_response_left_after_latest_wins_deduplication() -> None:
    payload = {
        "prior_unique_count": 1,
        "current_daily_counts": [
            {"date": "2026-08-07", "unique_count": 30},
            {"date": "2026-08-08", "unique_count": 2},
            {"date": "2026-08-10", "unique_count": 3},
        ],
        "total_unique_count": 36,
    }

    result = run_detector(payload)

    assert result == DetectionResult(
        is_new=True,
        survey_date=date(2026, 8, 7),
        reason="pre_open_response_exception",
    )


def test_rejects_late_responses_to_reported_survey() -> None:
    payload = {
        "prior_unique_count": 30,
        "current_daily_counts": [{"date": "2026-08-07", "unique_count": 3}],
        "total_unique_count": 33,
    }

    result = run_detector(payload)

    assert result == DetectionResult(
        is_new=False,
        survey_date=None,
        reason="late_response",
    )


def test_uses_first_current_response_when_no_history_exists() -> None:
    payload = {
        "prior_unique_count": 0,
        "current_daily_counts": [
            {"date": "2026-08-07", "unique_count": 1},
            {"date": "2026-08-08", "unique_count": 4},
        ],
        "total_unique_count": 5,
    }

    result = run_detector(payload)

    assert result == DetectionResult(
        is_new=True,
        survey_date=date(2026, 8, 7),
        reason="first_response",
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
