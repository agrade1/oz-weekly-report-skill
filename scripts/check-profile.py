# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pydantic>=2.11,<3",
#   "pyyaml>=6.0,<7",
# ]
# ///

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PROFILE = Path.home() / ".codex" / "oz-weekly-report" / "profile.yaml"

DEFAULT_SHEETS = {
    "dashboard": "창업가 대시보드",
    "learning": "창업가 학습",
    "operation": "창업가 운영",
    "roster": "창업가_수강생 주요 정보",
}

TEMPLATE = """version: 3

# 담당 과정과 기수
camp:
cohort:
cohort_query:
# 예: cohort가 "5기"이면 보통 "5"
report_label:
# 비워두면 "<camp> <cohort>"로 계산
roster_cohort_label:
# 예: 창업가 5기
roster_excluded_names: []
# 예: [홍길동, 김오즈]

# 원본 Google Sheets
satisfaction_dashboard_url:
roster_url:

# 탭 이름이 다르면 수정
sheets:
  dashboard: 창업가 대시보드
  learning: 창업가 학습
  operation: 창업가 운영
  roster: 창업가_수강생 주요 정보

# Notion 출력 및 헬스체크는 선택
notion_parent_url:
health_check_page_url:
health_check_data_source_url:

# 자동화 기본값
timezone: Asia/Seoul
schedule_mode: weekly_monday
# weekly_monday 또는 first_business_day
schedule_time: "10:30"
extra_holidays: []
"""


def compact(value: Any) -> str:
    return "" if value is None else str(value).strip()


def load_profile(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError("profile.yaml must contain a mapping")
    return loaded


def derived_cohort_query(profile: dict[str, Any]) -> str:
    explicit = compact(profile.get("cohort_query"))
    if explicit:
        return explicit.removesuffix("기")
    matched = re.search(r"\d+", compact(profile.get("cohort")))
    return matched.group(0) if matched else ""


def normalized_profile(profile: dict[str, Any]) -> dict[str, Any]:
    output = dict(profile)
    sheets = output.get("sheets")
    if not isinstance(sheets, dict):
        sheets = {}
    output["sheets"] = {**DEFAULT_SHEETS, **sheets}
    output["cohort_query"] = derived_cohort_query(output)
    if not compact(output.get("report_label")) and compact(output.get("camp")) and compact(output.get("cohort")):
        output["report_label"] = f"{compact(output.get('camp'))} {compact(output.get('cohort'))}"
    output.setdefault("roster_excluded_names", [])
    output.setdefault("timezone", "Asia/Seoul")
    output.setdefault("schedule_mode", "weekly_monday")
    output.setdefault("schedule_time", "10:30")
    output.setdefault("extra_holidays", [])
    return output


def missing_fields(profile: dict[str, Any]) -> list[str]:
    required = [
        "camp",
        "cohort",
        "cohort_query",
        "report_label",
        "roster_cohort_label",
        "satisfaction_dashboard_url",
        "roster_url",
        "timezone",
        "schedule_mode",
        "schedule_time",
    ]
    missing = [field for field in required if not compact(profile.get(field))]
    for key in ("dashboard", "learning", "operation", "roster"):
        if not compact(profile.get("sheets", {}).get(key)):
            missing.append(f"sheets.{key}")
    return missing


def setup_prompts(fields: list[str]) -> list[str]:
    descriptions = {
        "camp": "담당 과정명(예: 1인 창업가)",
        "cohort": "담당 기수 표시명(예: 5기)",
        "cohort_query": "만족도 대시보드 A/M열에서 검색할 기수 값(예: 5)",
        "report_label": "보고서/자동화 제목에 쓸 표시명(예: 창업가 5기)",
        "roster_cohort_label": "마스터시트 A열과 Notion 헬스체크의 정확한 기수명(예: 창업가 5기)",
        "satisfaction_dashboard_url": "[교육팀] 만족도 대시보드 Google Sheets URL",
        "roster_url": "마스터시트 Google Sheets URL",
        "timezone": "시간대(기본 Asia/Seoul)",
        "schedule_mode": "자동화 방식(weekly_monday 또는 first_business_day)",
        "schedule_time": "자동 실행 시각(HH:MM, 기본 10:30)",
        "sheets.dashboard": "만족도 대시보드 탭명",
        "sheets.learning": "학습 응답 원본 탭명",
        "sheets.operation": "운영 응답 원본 탭명",
        "sheets.roster": "마스터시트 재원 정보 탭명",
    }
    return [descriptions.get(field, field) for field in fields]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--init-missing", action="store_true")
    args = parser.parse_args()

    profile_path = Path(args.profile).expanduser()
    created = False
    if not profile_path.exists():
        if args.init_missing:
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            profile_path.write_text(TEMPLATE, encoding="utf-8")
            created = True
        else:
            print(json.dumps({"status": "missing_profile", "profile_path": str(profile_path)}, ensure_ascii=False))
            return

    profile = normalized_profile(load_profile(profile_path))
    missing = missing_fields(profile)
    status = "ready" if not missing else "needs_setup"
    print(
        json.dumps(
            {
                "status": status,
                "profile_path": str(profile_path),
                "created_template": created,
                "missing_fields": missing,
                "setup_prompts": setup_prompts(missing),
                "profile": profile if status == "ready" else None,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
