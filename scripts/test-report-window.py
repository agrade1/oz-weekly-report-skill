# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "holidays>=0.82,<1",
#   "pydantic>=2.11,<3",
#   "pytest>=8.4,<9",
# ]
# ///
# ─── How to run ───
# uv run test-report-window.py

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import ClassVar, Final

import pytest
from pydantic import BaseModel, ConfigDict

WINDOW_TOOL: Final = Path(__file__).with_name("report-window.py")


class WindowResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    comparison_start: datetime
    start: datetime
    end: datetime
    replay: bool
    should_run: bool
    first_business_day: date


def run_window(payload: dict[str, str | None]) -> WindowResult:
    completed = subprocess.run(
        [sys.executable, str(WINDOW_TOOL)],
        input=json.dumps(payload),
        check=True,
        capture_output=True,
        text=True,
    )
    return WindowResult.model_validate_json(completed.stdout)


def test_same_cutoff_replays_the_completed_week_instead_of_empty_window() -> None:
    result = run_window(
        {
            "run_at": "2026-08-12T15:00:00+09:00",
            "last_successful_report_at": "2026-08-10T10:30:00+09:00",
            "timezone": "Asia/Seoul",
        }
    )

    assert result.start.isoformat() == "2026-08-03T10:30:00+09:00"
    assert result.end.isoformat() == "2026-08-10T10:30:00+09:00"
    assert result.replay is True


def test_first_run_uses_the_latest_completed_week() -> None:
    result = run_window(
        {
            "run_at": "2026-08-12T15:00:00+09:00",
            "last_successful_report_at": None,
            "timezone": "Asia/Seoul",
        }
    )

    assert result.comparison_start.isoformat() == "2026-07-27T10:30:00+09:00"
    assert result.start.isoformat() == "2026-08-03T10:30:00+09:00"
    assert result.end.isoformat() == "2026-08-10T10:30:00+09:00"
    assert result.replay is False


def test_monday_holiday_runs_on_tuesday_only() -> None:
    monday = run_window(
        {
            "run_at": "2026-03-02T10:30:00+09:00",
            "last_successful_report_at": None,
            "timezone": "Asia/Seoul",
            "scheduled_run": True,
        }
    )
    tuesday = run_window(
        {
            "run_at": "2026-03-03T10:30:00+09:00",
            "last_successful_report_at": None,
            "timezone": "Asia/Seoul",
            "scheduled_run": True,
        }
    )

    assert monday.first_business_day.isoformat() == "2026-03-03"
    assert monday.should_run is False
    assert tuesday.should_run is True
    assert tuesday.end.isoformat() == "2026-03-03T10:30:00+09:00"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
