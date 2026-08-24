# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pydantic>=2.11,<3",
#   "pytest>=8.4,<9",
# ]
# ///
# ─── How to run ───
# uv run test-aggregate-metrics.py

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import ClassVar, Final

import pytest
from pydantic import BaseModel, ConfigDict, PositiveInt

CALCULATOR: Final = Path(__file__).with_name("aggregate-metrics.py")


class MetricResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    content: str
    live: str
    assignment: str
    achievement: str
    respondent_count: PositiveInt


def run_calculator(payload: str) -> MetricResult:
    completed = subprocess.run(
        [sys.executable, str(CALCULATOR)],
        input=payload,
        check=True,
        capture_output=True,
        text=True,
    )
    return MetricResult.model_validate_json(completed.stdout)


def test_dashboard_reference_fixture() -> None:
    payload = json.dumps(
        {
            "content": [4.75],
            "live": [4.722222222222222],
            "assignment": [4.472222222222222],
            "respondent_count": 36,
        }
    )

    result = run_calculator(payload)

    assert result == MetricResult(
        content="4.8",
        live="4.7",
        assignment="4.5",
        achievement="4.6",
        respondent_count=36,
    )


def test_rejects_empty_metric_array() -> None:
    payload = json.dumps(
        {
            "content": [],
            "live": [5],
            "assignment": [5],
            "respondent_count": 1,
        }
    )

    with pytest.raises(subprocess.CalledProcessError):
        _ = run_calculator(payload)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
