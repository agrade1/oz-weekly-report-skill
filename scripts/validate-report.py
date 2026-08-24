# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pydantic>=2.11,<3",
# ]
# ///
# ─── How to run ───
# printf '%s' '{"report":"...","required_originals":[],"long_originals":[],"special_issue_names":[],"operation_voc_required":false,"level_classes":[],"learning_subjects":[],"dashboard_required":false}' | uv run validate-report.py

from __future__ import annotations

import re
import sys
from collections import Counter
from typing import Annotated, ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field

WRITING_OPEN: Final = re.compile(
    r'^:::writing\{variant="document" id="\d{5}"\}\n'
)
MARKDOWN_CONTROLS: Final = frozenset("><#-+*`|")
TextList = Annotated[tuple[str, ...], Field(default_factory=tuple)]


class ValidationInput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    report: str
    required_originals: TextList
    long_originals: TextList
    special_issue_names: TextList
    operation_voc_required: bool
    level_classes: TextList
    learning_subjects: TextList
    dashboard_required: bool
    missing_response_names: TextList
    missing_response_required: bool
    source_warning_required: bool


def markdown_safe(original: str) -> str:
    leading = 0
    for character in original:
        if character in MARKDOWN_CONTROLS:
            leading += 1
        else:
            break
    if leading == 0:
        return original
    prefix = "".join(f"\\{character}" for character in original[:leading])
    return prefix + original[leading:]


def section_order(payload: ValidationInput) -> tuple[str, ...]:
    sections = ["## 정량 보고"]
    if payload.missing_response_required or payload.source_warning_required:
        sections.append("## 미응답 수강생")
    if payload.special_issue_names:
        sections.append("## 특이사항")
    if payload.operation_voc_required:
        sections.append("운만조 VOC 요약")
    sections.extend(f"학만조 VOC _{subject}" for subject in payload.learning_subjects)
    if payload.dashboard_required:
        sections.append("## 운영 대시보드 입력용")
    return tuple(sections)


def special_issue_section(report: str) -> str:
    start = report.find("## 특이사항")
    if start < 0:
        return ""
    end = report.find("\n## ", start + len("## 특이사항"))
    return report[start:] if end < 0 else report[start:end]


def missing_response_section(report: str) -> str:
    start = report.find("## 미응답 수강생")
    if start < 0:
        return ""
    end = report.find("\n## ", start + len("## 미응답 수강생"))
    return report[start:] if end < 0 else report[start:end]


def validate_special_issue(issues: str, name: str) -> tuple[str, ...]:
    heading = re.compile(
        rf"^- \*\*{re.escape(name)} — (?P<title>.+?)\*\*\s*$", re.MULTILINE
    )
    matches = tuple(heading.finditer(issues))
    if len(matches) != 1:
        return (f"특이사항 인물 누락 또는 중복: {name} (실제 {len(matches)})",)
    match = matches[0]
    next_heading = re.search(r"^- \*\*.+? — .+?\*\*\s*$", issues[match.end() :], re.MULTILINE)
    block_end = match.end() + next_heading.start() if next_heading else len(issues)
    block = issues[match.end() : block_end]
    errors: list[str] = []
    if "검토" in match.group("title"):
        errors.append(f"특이사항 문제 제목이 구체적이지 않음: {name}")
    situation = re.search(
        r"`상황`\s*\n(?P<body>.*?)(?=\n\s*`운영진 대응 및 결과`)",
        block,
        re.DOTALL,
    )
    if situation is None or re.search(r"^\s+-\s+\S", situation.group("body"), re.MULTILINE) is None:
        errors.append(f"특이사항 상황 근거 누락: {name}")
    response = re.search(r"`운영진 대응 및 결과`\s*\n(?P<body>.*)$", block, re.DOTALL)
    if response is None or re.search(r"^\s+-\s+\S", response.group("body"), re.MULTILINE) is None:
        errors.append(f"특이사항 대응 내용 누락: {name}")
    return tuple(errors)


def validate(payload: ValidationInput) -> tuple[str, ...]:
    errors: list[str] = []
    report = payload.report
    if WRITING_OPEN.match(report) is None or not report.endswith("\n:::"):
        errors.append("Writing 블록 형식 누락")
    positions = tuple(report.find(section) for section in section_order(payload))
    if any(position < 0 for position in positions):
        missing = tuple(
            section
            for section, position in zip(section_order(payload), positions, strict=True)
            if position < 0
        )
        errors.extend(f"필수 섹션 누락: {section}" for section in missing)
    elif positions != tuple(sorted(positions)):
        errors.append("섹션 순서 위반")
    for level_class in payload.level_classes:
        if f"- **{level_class}**" not in report:
            errors.append(f"수준별 학습반 누락: {level_class}")
    expected_originals = Counter(markdown_safe(item) for item in payload.required_originals)
    for original, expected_count in expected_originals.items():
        actual_count = report.count(original)
        if actual_count < expected_count:
            errors.append(f"원문 누락: {original} (기대 {expected_count}, 실제 {actual_count})")
    for original in payload.long_originals:
        safe_original = markdown_safe(original)
        original_at = report.find(safe_original)
        toggle_at = report.rfind("원문 보기", 0, original_at)
        if original_at < 0 or toggle_at < max(0, original_at - 600):
            errors.append(f"긴 원문 보기 구조 누락: {original}")
    issues = special_issue_section(report)
    for name in payload.special_issue_names:
        errors.extend(validate_special_issue(issues, name))
    missing = missing_response_section(report)
    expected_missing = Counter(payload.missing_response_names)
    for name, expected_count in expected_missing.items():
        actual_count = missing.count(name)
        if actual_count < expected_count:
            errors.append(f"미응답 수강생 누락: {name} (기대 {expected_count}, 실제 {actual_count})")
    if payload.source_warning_required and "데이터 확인 필요" not in missing:
        errors.append("원천 데이터 불일치 경고 누락")
    if "<details" in report or "<summary" in report:
        errors.append("Notion 비호환 HTML 포함")
    return tuple(errors)


def main() -> None:
    payload = ValidationInput.model_validate_json(sys.stdin.read())
    errors = validate(payload)
    if errors:
        _ = sys.stderr.write("\n".join(errors) + "\n")
        raise SystemExit(1)
    _ = sys.stdout.write('{"valid":true}\n')


if __name__ == "__main__":
    main()
