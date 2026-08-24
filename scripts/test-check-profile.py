# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pydantic>=2.11,<3",
#   "pytest>=8.4,<9",
#   "pyyaml>=6.0,<7",
# ]
# ///
# ─── How to run ───
# uv run test-check-profile.py

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest

CHECKER: Final = Path(__file__).with_name("check-profile.py")


def test_creates_template_and_reports_missing_setup(tmp_path: Path) -> None:
    profile = tmp_path / "profile.yaml"
    completed = subprocess.run(
        [sys.executable, str(CHECKER), "--profile", str(profile), "--init-missing"],
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)

    assert profile.exists()
    assert result["status"] == "needs_setup"
    assert result["created_template"] is True
    assert "satisfaction_dashboard_url" in result["missing_fields"]
    assert "담당 과정명(예: 1인 창업가)" in result["setup_prompts"]


def test_derives_profile_defaults(tmp_path: Path) -> None:
    profile = tmp_path / "profile.yaml"
    profile.write_text(
        "\n".join(
            [
                "version: 3",
                "camp: 1인 창업가",
                "cohort: 6기",
                "roster_cohort_label: 창업가 6기",
                "satisfaction_dashboard_url: https://docs.google.com/spreadsheets/d/source/edit",
                "roster_url: https://docs.google.com/spreadsheets/d/roster/edit",
            ]
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(CHECKER), "--profile", str(profile)],
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)

    assert result["status"] == "ready"
    assert result["profile"]["cohort_query"] == "6"
    assert result["profile"]["report_label"] == "1인 창업가 6기"
    assert result["profile"]["sheets"]["dashboard"] == "창업가 대시보드"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
