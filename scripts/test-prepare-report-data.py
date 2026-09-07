# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pydantic>=2.11,<3",
#   "pytest>=8.4,<9",
# ]
# ///
# ─── How to run ───
# uv run test-prepare-report-data.py

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest

PREPARER: Final = Path(__file__).with_name("prepare-report-data.py")


def operation_row(
    name: str,
    score: int,
    reason: str | None,
    other: str | None,
    submitted_at: str,
) -> list[str | int | None]:
    return [
        5,
        name,
        score,
        reason,
        other,
        submitted_at,
        f"token-{name}-{submitted_at}",
    ]


def learning_row(
    name: str,
    content: int,
    live: int,
    assignment: int,
    voc: str,
    submitted_at: str,
) -> list[str | int | None]:
    return [
        5,
        name,
        "UI 디자인 실무",
        content,
        live,
        3,
        assignment,
        3,
        voc,
        None,
        None,
        submitted_at,
        f"token-{name}-{submitted_at}",
    ]


def test_partitions_cohort_deduplicates_and_builds_complete_manifest() -> None:
    payload = {
        "cohort": "5기",
        "comparison_start": "2026-07-27T10:30:00+09:00",
        "start": "2026-08-03T10:30:00+09:00",
        "end": "2026-08-10T10:30:00+09:00",
        "operation_rows": [
            operation_row("지난", 4, "지난주 원문", None, "2026. 7. 31 오전 10:00:00"),
            operation_row("앨리스", 5, "삭제될 원문", None, "2026-08-07T09:00:00+09:00"),
            operation_row("앨리스", 4, "최신 운영 원문", "운영 제안", "2026-08-08T09:00:00+09:00"),
            operation_row("밥", 2, "속도 빠름", None, "2026-08-07T10:00:00+09:00"),
            [12, "다른기수", 1, "절대 출력 금지", None, "2026-08-07T10:00:00+09:00", "other"],
        ],
        "learning_dashboard_rows": [[5, "UI 디자인 실무", "2026-08-06", 3, 5, None, 4.8, 5.0, 4.4, 4.7]],
        "operation_dashboard_rows": [["8월 1주차", 5, "2026-08-07", 3, 2, None, 3.0]],
        "roster_rows": [
            ["창업가 5기", None, "앨리스", None, "훈련중"],
            ["창업가 5기", None, "밥", None, "훈련중"],
            ["창업가 5기", None, "찰리", None, "훈련중"],
        ],
        "roster_cohort_label": "창업가 5기",
        "learning_rows": [
            learning_row("앨리스", 3, 3, 3, "삭제될 학습 원문", "2026-07-26T10:00:00+09:00"),
            learning_row("앨리스", 5, 5, 5, "학습 원문", "2026-08-07T07:00:00+09:00"),
            learning_row("밥", 4, 5, 2, "과제가 어려웠습니다", "2026-08-08T07:01:00+09:00"),
            learning_row("찰리", 5, 5, 5, "좋아요", "2026-08-07T07:02:00+09:00"),
            learning_row("다나", 5, 5, 5, "유익했습니다", "2026-08-07T07:03:00+09:00"),
            learning_row("에반", 5, 5, 5, "감사합니다", "2026-08-07T07:04:00+09:00"),
        ],
    }
    completed = subprocess.run(
        [sys.executable, str(PREPARER)],
        input=json.dumps(payload, ensure_ascii=False),
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)

    assert result["operation"]["previous"]["score"] == "4.0"
    assert result["operation"]["current"] == {
        "score": "3.0", "respondent_count": 2, "survey_date": "2026-08-07",
        "current_count": 3, "dashboard_response_count": 2,
    }
    assert [item["original"] for item in result["operation"]["general_voc"]] == ["최신 운영 원문", "운영 제안", "속도 빠름"]
    assert result["operation"]["level_classes"] == []
    assert result["learning"][0]["metrics"] == {
        "content": "4.8",
        "live": "5.0",
        "assignment": "4.4",
        "achievement": "4.7",
        "respondent_count": 5,
        "current_count": 3,
        "dashboard_response_count": 5,
    }
    assert result["learning"][0]["survey_date"] == "2026-08-07"
    assert result["validation"]["required_originals"] == [
        "최신 운영 원문",
        "운영 제안",
        "속도 빠름",
        "학습 원문",
        "과제가 어려웠습니다",
        "좋아요",
        "유익했습니다",
        "감사합니다",
    ]
    assert result["validation"]["special_issue_names"] == ["밥"]
    assert result["special_issues"][0]["learning_scores"][0]["assignment"] == 2
    assert result["missing_responses"][0] == {"survey": "운영 만족도", "subject": None, "names": ["찰리"]}
    assert result["missing_responses"][1]["names"] == []
    assert "절대 출력 금지" not in completed.stdout
    assert "삭제될 원문" not in completed.stdout


def test_adds_recent_health_check_risk_to_special_issues() -> None:
    payload = {
        "cohort": "5기",
        "comparison_start": "2026-08-03T10:30:00+09:00",
        "start": "2026-08-03T10:30:00+09:00",
        "end": "2026-08-10T10:30:00+09:00",
        "operation_rows": [],
        "learning_dashboard_rows": [],
        "operation_dashboard_rows": [],
        "roster_rows": [
            ["창업가 5기", None, "민규", None, "훈련중"],
            ["창업가 5기", None, "앨리스", None, "훈련중"],
            ["창업가 5기", None, "오래전", None, "훈련중"],
        ],
        "roster_cohort_label": "창업가 5기",
        "learning_rows": [],
        "health_check_notes": [
            {
                "name": "민규",
                "checked_at": "2026-08-05",
                "cycle": "2차",
                "labels": ["불만", "학습고민"],
                "note": "수업 설명과 운영 피로를 호소함",
                "url": "https://app.notion.com/p/example",
            },
            {
                "name": "앨리스",
                "checked_at": "2026-08-05",
                "cycle": "2차",
                "labels": ["열정"],
                "note": "긍정 상태",
            },
            {
                "name": "오래전",
                "checked_at": "2026-07-01",
                "cycle": "1차",
                "labels": ["불만"],
                "note": "보고 기간 밖의 과거 이슈",
            },
        ],
    }
    completed = subprocess.run(
        [sys.executable, str(PREPARER)],
        input=json.dumps(payload, ensure_ascii=False),
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)

    assert result["validation"]["special_issue_names"] == ["민규"]
    assert result["special_issues"][0]["health_checks"] == [
        {
            "name": "민규",
            "checked_at": "2026-08-05",
            "cycle": "2차",
            "labels": ["불만", "학습고민"],
            "note": "수업 설명과 운영 피로를 호소함",
            "url": "https://app.notion.com/p/example",
        }
    ]
    assert "보고 기간 밖의 과거 이슈" not in completed.stdout


def test_applies_profile_roster_excluded_names_to_missing_respondents() -> None:
    payload = {
        "cohort": "5기",
        "comparison_start": "2026-07-27T10:30:00+09:00",
        "start": "2026-08-03T10:30:00+09:00",
        "end": "2026-08-10T10:30:00+09:00",
        "operation_rows": [
            operation_row("앨리스", 5, None, None, "2026-08-07T09:00:00+09:00"),
        ],
        "learning_dashboard_rows": [],
        "operation_dashboard_rows": [["8월 1주차", 5, "2026-08-07", 3, 1, None, 5.0]],
        "roster_rows": [
            ["창업가 5기", None, "앨리스", None, "훈련중"],
            ["창업가 5기", None, "제외대상A", None, "훈련중"],
            ["창업가 5기", None, "제외대상B", None, "훈련중"],
        ],
        "roster_cohort_label": "창업가 5기",
        "roster_excluded_names": ["제외대상A", "제외대상B"],
        "learning_rows": [],
    }
    completed = subprocess.run(
        [sys.executable, str(PREPARER)],
        input=json.dumps(payload, ensure_ascii=False),
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)

    assert result["missing_responses"] == [{"survey": "운영 만족도", "subject": None, "names": []}]
    assert result["source_warnings"] == [
        "운영 만족도 현재 인원 불일치: 대시보드 3명 / 마스터시트 훈련중(내부 제외 반영) 1명"
    ]


def test_operation_uses_latest_dashboard_survey_date_not_entire_report_window() -> None:
    payload = {
        "cohort": "5기",
        "comparison_start": "2026-08-24T10:00:00+09:00",
        "start": "2026-08-31T10:30:00+09:00",
        "end": "2026-09-07T10:00:00+09:00",
        "operation_rows": [
            operation_row("지난응답", 5, "지난 조사 의견", None, "2026. 8. 29 오전 9:00:00"),
            operation_row("민규", 5, "9월 2일 응답", None, "2026. 9. 2 오전 1:03:32"),
            operation_row("김규환", 5, None, None, "2026. 9. 4 오전 1:12:30"),
            operation_row("김하영", 5, None, "코칭 받고 싶습니다", "2026. 9. 4 오전 1:35:25"),
            operation_row("문동율", 4, None, "리뷰 시간이 있으면 좋겠습니다", "2026. 9. 4 오전 8:51:26"),
            operation_row("정지호", 5, None, "X", "2026. 9. 7 오전 12:42:15"),
        ],
        "learning_dashboard_rows": [],
        "operation_dashboard_rows": [
            ["8월 5주차", 5, "2026-08-28", 4, 2, None, 5.0],
            ["9월 1주차", 5, "2026-09-04", 4, 4, None, 4.8],
        ],
        "roster_rows": [
            ["창업가 5기", None, "민규", None, "훈련중"],
            ["창업가 5기", None, "김규환", None, "훈련중"],
            ["창업가 5기", None, "김하영", None, "훈련중"],
            ["창업가 5기", None, "문동율", None, "훈련중"],
            ["창업가 5기", None, "정지호", None, "훈련중"],
        ],
        "roster_cohort_label": "창업가 5기",
        "learning_rows": [],
    }
    completed = subprocess.run(
        [sys.executable, str(PREPARER)],
        input=json.dumps(payload, ensure_ascii=False),
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)

    assert result["operation"]["current"] == {
        "score": "4.8", "respondent_count": 4, "survey_date": "2026-09-04",
        "current_count": 4, "dashboard_response_count": 4,
    }
    assert result["operation"]["previous"] == {
        "score": "5.0", "respondent_count": 2, "survey_date": "2026-08-29",
        "current_count": None, "dashboard_response_count": None,
    }
    assert result["missing_responses"] == [{"survey": "운영 만족도", "subject": None, "names": ["민규"]}]
    assert [item["original"] for item in result["operation"]["general_voc"]] == [
        "코칭 받고 싶습니다",
        "리뷰 시간이 있으면 좋겠습니다",
    ]
    assert "9월 2일 응답" not in completed.stdout


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
