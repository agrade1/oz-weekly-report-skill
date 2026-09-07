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

DEFAULT_SOURCE_DISCOVERY = {
    "satisfaction_dashboard_query": "[교육팀] 만족도 대시보드",
    "roster_query": "마스터시트",
}

CAMP_PRESETS = {
    "entrepreneur": {
        "aliases": ("창업가", "1인 창업가", "1인창업가", "창업가캠프", "1인창업가캠프", "1인창업가부트캠프"),
        "label_prefix": "창업가",
        "sheets": {
            "dashboard": "창업가 대시보드",
            "learning": "창업가 학습",
            "operation": "창업가 운영",
            "roster": "창업가_수강생 주요 정보",
        },
    },
    "designer": {
        "aliases": ("디자이너", "디자인", "디자이너캠프", "디자인캠프", "디자이너부트캠프"),
        "label_prefix": "디자이너",
        "sheets": {
            "dashboard": "디자이너 대시보드",
            "learning": "디자이너 학습",
            "operation": "디자이너 운영",
            "roster": "디자이너_수강생 주요 정보",
        },
    },
}

TEMPLATE = """version: 3

# 담당 캠프 preset과 기수
# camp는 예: 창업가 또는 디자이너
camp:
# 예: 5기
cohort:
cohort_query:
report_label:
roster_cohort_label:
roster_excluded_names: []
# 예: [홍길동, 김오즈]

# 원본 Google Sheets
satisfaction_dashboard_url:
roster_url:

# 탭 이름이 다르면 수정
sheets:
  dashboard:
  learning:
  operation:
  roster:

# Codex가 Google Drive에서 후보를 찾을 때 쓰는 기본 검색어
source_discovery:
  satisfaction_dashboard_query: "[교육팀] 만족도 대시보드"
  roster_query: "마스터시트"

# Notion 출력 및 헬스체크는 선택
notion_parent_url:
health_check_page_url:
health_check_data_source_url:

# 자동화 기본값
timezone: Asia/Seoul
schedule_mode: weekly_monday
# weekly_monday 또는 first_business_day
schedule_time: "10:00"
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


def write_profile(path: Path, profile: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(profile, allow_unicode=True, sort_keys=False), encoding="utf-8")


def preset_key(value: Any) -> str:
    return re.sub(r"[\s_\-]+", "", compact(value).replace("부트캠프", "").replace("캠프", "")).lower()


def selected_preset(profile: dict[str, Any]) -> dict[str, Any] | None:
    wanted = preset_key(profile.get("camp_preset") or profile.get("camp"))
    if not wanted:
        return None
    for preset in CAMP_PRESETS.values():
        aliases = {preset_key(alias) for alias in preset["aliases"]}
        if wanted in aliases:
            return preset
    return None


def derived_cohort_query(profile: dict[str, Any]) -> str:
    explicit = compact(profile.get("cohort_query"))
    if explicit:
        return explicit.removesuffix("기")
    matched = re.search(r"\d+", compact(profile.get("cohort")))
    return matched.group(0) if matched else ""


def cohort_display(value: Any) -> str:
    text = compact(value)
    return f"{text}기" if re.fullmatch(r"\d+", text) else text


def normalized_profile(profile: dict[str, Any]) -> dict[str, Any]:
    output = dict(profile)
    if compact(output.get("cohort")):
        output["cohort"] = cohort_display(output.get("cohort"))
    preset = selected_preset(output)
    sheets = output.get("sheets")
    if not isinstance(sheets, dict):
        sheets = {}
    preset_sheets = preset["sheets"] if preset else {}
    output["sheets"] = {**preset_sheets, **{key: value for key, value in sheets.items() if compact(value)}}
    output["cohort_query"] = derived_cohort_query(output)
    label_prefix = compact(preset["label_prefix"]) if preset else compact(output.get("camp"))
    if not compact(output.get("report_label")) and label_prefix and compact(output.get("cohort")):
        output["report_label"] = f"{label_prefix} {compact(output.get('cohort'))}"
    if not compact(output.get("roster_cohort_label")) and compact(output.get("report_label")):
        output["roster_cohort_label"] = compact(output.get("report_label"))
    output.setdefault("roster_excluded_names", [])
    discovery = output.get("source_discovery")
    if not isinstance(discovery, dict):
        discovery = {}
    output["source_discovery"] = {**DEFAULT_SOURCE_DISCOVERY, **{key: value for key, value in discovery.items() if compact(value)}}
    output.setdefault("timezone", "Asia/Seoul")
    output.setdefault("schedule_mode", "weekly_monday")
    output.setdefault("schedule_time", "10:00")
    output.setdefault("extra_holidays", [])
    return output


def missing_fields(profile: dict[str, Any]) -> list[str]:
    first_stage = [field for field in ("camp", "cohort") if not compact(profile.get(field))]
    if first_stage:
        return first_stage

    required = [
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


def setup_stage(missing: list[str]) -> str:
    if not missing:
        return "ready"
    if any(field in {"camp", "cohort"} for field in missing):
        return "cohort_selection"
    if any(field in {"satisfaction_dashboard_url", "roster_url"} for field in missing):
        return "source_discovery"
    return "profile_completion"


def setup_prompts(fields: list[str]) -> list[str]:
    descriptions = {
        "camp": "담당 캠프 선택(예: 창업가 또는 디자이너)",
        "cohort": "담당 기수 표시명(예: 5기)",
        "cohort_query": "만족도 대시보드 A/M열에서 검색할 기수 값(예: 5)",
        "report_label": "보고서/자동화 제목에 쓸 표시명(예: 창업가 5기)",
        "roster_cohort_label": "마스터시트 A열과 Notion 헬스체크의 정확한 기수명(예: 창업가 5기)",
        "satisfaction_dashboard_url": "Google Drive에서 [교육팀] 만족도 대시보드 후보를 찾거나, 찾지 못하면 해당 Sheets URL",
        "roster_url": "Google Drive에서 마스터시트 후보를 찾거나, 찾지 못하면 해당 Sheets URL",
        "timezone": "시간대(기본 Asia/Seoul)",
        "schedule_mode": "자동화 방식(weekly_monday 또는 first_business_day)",
        "schedule_time": "자동 실행 시각(HH:MM, 기본 10:00)",
        "sheets.dashboard": "만족도 대시보드 탭명",
        "sheets.learning": "학습 응답 원본 탭명",
        "sheets.operation": "운영 응답 원본 탭명",
        "sheets.roster": "마스터시트 재원 정보 탭명",
    }
    return [descriptions.get(field, field) for field in fields]


def setup_hints(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "cohort_selection_prompt": "담당 캠프와 기수를 알려주세요. 예: 창업가 5기 / 디자이너 3기",
        "drive_search": {
            "satisfaction_dashboard_query": profile.get("source_discovery", {}).get("satisfaction_dashboard_query"),
            "roster_query": profile.get("source_discovery", {}).get("roster_query"),
            "expected_tabs": profile.get("sheets", {}),
            "roster_cohort_label": profile.get("roster_cohort_label"),
        },
        "default_automation": {
            "schedule_mode": profile.get("schedule_mode"),
            "timezone": profile.get("timezone"),
            "schedule_time": profile.get("schedule_time"),
        },
    }


def coerce_set_value(key: str, value: str) -> Any:
    if key in {"roster_excluded_names", "extra_holidays"}:
        return [item.strip() for item in value.split(",") if item.strip()]
    return value.strip()


def apply_setter(profile: dict[str, Any], setter: str) -> None:
    if "=" not in setter:
        raise ValueError(f"--set value must be key=value: {setter}")
    key, value = setter.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError("--set key cannot be blank")
    target = profile
    parts = key.split(".")
    for part in parts[:-1]:
        current = target.get(part)
        if not isinstance(current, dict):
            current = {}
            target[part] = current
        target = current
    target[parts[-1]] = coerce_set_value(key, value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--init-missing", action="store_true")
    parser.add_argument("--set", dest="setters", action="append", default=[], metavar="KEY=VALUE")
    args = parser.parse_args()

    profile_path = Path(args.profile).expanduser()
    created = False
    updated = False
    if not profile_path.exists():
        if args.init_missing and not args.setters:
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            profile_path.write_text(TEMPLATE, encoding="utf-8")
            created = True
        elif args.init_missing or args.setters:
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            profile_path.write_text("version: 3\n", encoding="utf-8")
            created = True
        else:
            print(json.dumps({"status": "missing_profile", "profile_path": str(profile_path)}, ensure_ascii=False))
            return

    loaded_profile = load_profile(profile_path)
    for setter in args.setters:
        apply_setter(loaded_profile, setter)
    if args.setters:
        loaded_profile = normalized_profile(loaded_profile)
        write_profile(profile_path, loaded_profile)
        updated = True

    profile = normalized_profile(loaded_profile)
    missing = missing_fields(profile)
    status = "ready" if not missing else "needs_setup"
    print(
        json.dumps(
            {
                "status": status,
                "profile_path": str(profile_path),
                "created_template": created,
                "updated_profile": updated,
                "setup_stage": setup_stage(missing),
                "missing_fields": missing,
                "setup_prompts": setup_prompts(missing),
                "setup_hints": setup_hints(profile),
                "profile": profile if status == "ready" else None,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
