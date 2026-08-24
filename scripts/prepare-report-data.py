# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pydantic>=2.11,<3",
# ]
# ///

from __future__ import annotations

import sys
from collections import Counter
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Final

from report_data_models import (
    HealthCheckNote,
    ONE_DECIMAL,
    LearningScore,
    LearningSummary,
    MetricSummary,
    MissingResponseGroup,
    OperationPeriod,
    OperationSummary,
    PreparedReport,
    PrepareInput,
    Row,
    SpecialIssue,
    ValidationContract,
    VocItem,
)
from report_row_values import normalize_cohort, normalize_name, score, submitted_at, valid_voc, value

HEALTH_CHECK_RISK_LABELS: Final = frozenset(
    {
        "불만",
        "학습고민",
        "독려",
        "강성",
        "이슈상담",
        "진로상담",
        "하차예정",
        "하차",
        "관심이 필요함",
        "수강철회",
        "출결문의",
        "회피형",
        "소심함",
        "고민",
        "😣",
        "🤐",
    }
)
MAX_HEALTH_CHECKS_PER_PERSON: Final = 2


def in_window(timestamp: datetime, start: datetime, end: datetime) -> bool:
    return start < timestamp <= end


def cohort_rows(rows: tuple[Row, ...], cohort: str) -> tuple[Row, ...]:
    return tuple(row for row in rows if normalize_cohort(value(row, 0)) == cohort)


def deduplicate(rows: tuple[Row, ...], name_index: int, timestamp_index: int) -> tuple[Row, ...]:
    latest: dict[str, Row] = {}
    for row in rows:
        name = normalize_name(value(row, name_index))
        if not name:
            continue
        current = latest.get(name)
        if current is None or submitted_at(value(current, timestamp_index)) < submitted_at(value(row, timestamp_index)):
            latest[name] = row
    return tuple(latest.values())


def display(raw: Decimal) -> str:
    return format(raw.quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP), ".1f")


def survey_date(rows: tuple[Row, ...], timestamp_index: int) -> date | None:
    if not rows:
        return None
    counts = Counter(submitted_at(value(row, timestamp_index)).date() for row in rows)
    wave = tuple(day for day, count in sorted(counts.items()) if count >= 5)
    return wave[0] if wave else min(counts)


def count_value(raw: object) -> int | None:
    if raw is None or str(raw).strip() == "":
        return None
    return int(Decimal(str(raw)))


def dashboard_day(raw: object) -> date | None:
    if raw is None or str(raw).strip() == "":
        return None
    return submitted_at(raw).date()


def operation_dashboard_match(rows: tuple[Row, ...], cohort: str, day: date | None) -> Row | None:
    if day is None:
        return None
    matches = tuple(
        row
        for row in rows
        if normalize_cohort(value(row, 1)) == cohort and dashboard_day(value(row, 2)) == day
    )
    return matches[-1] if matches else None


def learning_dashboard_match(rows: tuple[Row, ...], cohort: str, subject: str, day: date) -> Row | None:
    matches = tuple(
        row
        for row in rows
        if normalize_cohort(value(row, 0)) == cohort
        and str(value(row, 1) or "").strip() == subject
        and dashboard_day(value(row, 2)) is not None
    )
    if not matches:
        return None
    closest = min(matches, key=lambda row: abs((dashboard_day(value(row, 2)) - day).days))
    closest_day = dashboard_day(value(closest, 2))
    return closest if closest_day is not None and abs((closest_day - day).days) <= 7 else None


def operation_period(rows: tuple[Row, ...], dashboard_rows: tuple[Row, ...], cohort: str) -> OperationPeriod:
    if not rows:
        return OperationPeriod(
            score=None,
            respondent_count=0,
            survey_date=None,
            current_count=None,
            dashboard_response_count=None,
        )
    scores = tuple(score(value(row, 2)) for row in rows)
    mean = sum((Decimal(item) for item in scores), start=Decimal(0)) / Decimal(len(scores))
    day = survey_date(rows, 5)
    dashboard = operation_dashboard_match(dashboard_rows, cohort, day)
    return OperationPeriod(
        score=display(mean),
        respondent_count=len(rows),
        survey_date=day,
        current_count=count_value(value(dashboard, 3)) if dashboard else None,
        dashboard_response_count=count_value(value(dashboard, 4)) if dashboard else None,
    )


def operation_voc(rows: tuple[Row, ...]) -> tuple[VocItem, ...]:
    output: list[VocItem] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        name = str(value(row, 1)).strip()
        label = f"{score(value(row, 2))}점"
        for field, index in (("D", 3), ("E", 4)):
            original = valid_voc(value(row, index))
            key = (normalize_name(name), original or "")
            if original is not None and key not in seen:
                seen.add(key)
                output.append(VocItem(name=name, original=original, score_label=label, source_field=field))
    return tuple(output)


def metric_summary(rows: tuple[Row, ...], dashboard: Row | None) -> MetricSummary:
    content = tuple(Decimal(score(value(row, 3))) for row in rows)
    live = tuple(Decimal(score(value(row, 4))) for row in rows)
    assignment = tuple(Decimal(score(value(row, 6))) for row in rows)
    content_mean = sum(content, start=Decimal(0)) / Decimal(len(content))
    live_mean = sum(live, start=Decimal(0)) / Decimal(len(live))
    assignment_mean = sum(assignment, start=Decimal(0)) / Decimal(len(assignment))
    return MetricSummary(
        content=display(content_mean),
        live=display(live_mean),
        assignment=display(assignment_mean),
        achievement=display((content_mean + live_mean + assignment_mean) / Decimal(3)),
        respondent_count=len(rows),
        current_count=count_value(value(dashboard, 3)) if dashboard else None,
        dashboard_response_count=count_value(value(dashboard, 4)) if dashboard else None,
    )


def learning_surveys(
    rows: tuple[Row, ...],
    start: datetime,
    end: datetime,
    dashboard_rows: tuple[Row, ...],
    cohort: str,
) -> tuple[tuple[LearningSummary, tuple[Row, ...]], ...]:
    through_end = tuple(row for row in rows if submitted_at(value(row, 11)) <= end)
    current_subjects = tuple(
        dict.fromkeys(
            str(value(row, 2)).strip()
            for row in through_end
            if in_window(submitted_at(value(row, 11)), start, end)
        )
    )
    output: list[tuple[LearningSummary, tuple[Row, ...]]] = []
    for subject in current_subjects:
        subject_rows = tuple(row for row in through_end if str(value(row, 2)).strip() == subject)
        latest = deduplicate(subject_rows, 1, 11)
        current = tuple(row for row in latest if in_window(submitted_at(value(row, 11)), start, end))
        prior = tuple(row for row in latest if submitted_at(value(row, 11)) <= start)
        daily = Counter(submitted_at(value(row, 11)).date() for row in current)
        exception = (
            len(prior) <= 3
            and len(current) >= 5
            and any(count >= 5 for count in daily.values())
            and len(current) * 10 >= len(latest) * 7
        )
        if prior and not exception:
            continue
        included = latest if prior else current
        day = min(day for day, count in daily.items() if count >= 5) if exception else min(daily)
        dashboard = learning_dashboard_match(dashboard_rows, cohort, subject, day)
        voc = tuple(
            VocItem(
                name=str(value(row, 1)).strip(),
                original=original,
                score_label=f"콘텐츠 {score(value(row, 3))}점·실시간 {score(value(row, 4))}점·과제 {score(value(row, 6))}점",
                source_field="I",
            )
            for row in included
            if (original := valid_voc(value(row, 8))) is not None
        )
        output.append(
            (
                LearningSummary(
                    subject=subject,
                    survey_date=day,
                    metrics=metric_summary(included, dashboard),
                    voc=voc,
                ),
                included,
            )
        )
    return tuple(output)


def active_roster(rows: tuple[Row, ...], cohort_label: str, excluded_names: tuple[str, ...] = ()) -> tuple[str, ...]:
    expected = normalize_name(cohort_label)
    excluded = {normalize_name(name) for name in excluded_names}
    output: dict[str, str] = {}
    for row in rows:
        if normalize_name(value(row, 0)) != expected:
            continue
        if str(value(row, 4) or "").strip() != "훈련중":
            continue
        displayed = str(value(row, 2) or "").strip()
        normalized = normalize_name(displayed)
        if normalized and normalized not in excluded:
            output.setdefault(normalized, displayed)
    return tuple(output.values())


def missing_names(roster: tuple[str, ...], response_rows: tuple[Row, ...]) -> tuple[str, ...]:
    responded = {normalize_name(value(row, 1)) for row in response_rows}
    return tuple(name for name in roster if normalize_name(name) not in responded)


def source_warnings(
    roster: tuple[str, ...],
    operation: OperationPeriod,
    learning: tuple[LearningSummary, ...],
    roster_count_label: str = "마스터시트 훈련중",
) -> tuple[str, ...]:
    warnings: list[str] = []
    if not roster:
        warnings.append("훈련중 재원 명단을 확인할 수 없음")
    counts = (
        [("운영 만족도", operation.current_count, operation.respondent_count, operation.dashboard_response_count)]
        if operation.survey_date
        else []
    )
    counts.extend(
        (f"학습 만족도({survey.subject})", survey.metrics.current_count, survey.metrics.respondent_count, survey.metrics.dashboard_response_count)
        for survey in learning
    )
    for label, current_count, computed_responses, dashboard_responses in counts:
        if current_count is None:
            warnings.append(f"{label} 대시보드 현재 인원을 확인할 수 없음")
        elif roster and current_count != len(roster):
            warnings.append(f"{label} 현재 인원 불일치: 대시보드 {current_count}명 / {roster_count_label} {len(roster)}명")
        if dashboard_responses is None:
            warnings.append(f"{label} 대시보드 응답 인원을 확인할 수 없음")
        elif dashboard_responses != computed_responses:
            warnings.append(f"{label} 응답 인원 불일치: 대시보드 {dashboard_responses}명 / 원본 중복 제거 {computed_responses}명")
    return tuple(dict.fromkeys(warnings))


def clean_health_check(note: HealthCheckNote, end_day: date) -> HealthCheckNote | None:
    name = str(note.name or "").strip()
    if not normalize_name(name):
        return None
    if note.checked_at is not None and note.checked_at > end_day:
        return None
    labels = tuple(label.strip() for label in note.labels if label and label.strip())
    text = str(note.note or "").strip() or None
    cycle = str(note.cycle or "").strip() or None
    url = str(note.url or "").strip() or None
    return HealthCheckNote(name=name, checked_at=note.checked_at, cycle=cycle, labels=labels, note=text, url=url)


def health_check_index(notes: tuple[HealthCheckNote, ...], end_day: date) -> dict[str, tuple[HealthCheckNote, ...]]:
    grouped: dict[str, list[HealthCheckNote]] = {}
    for note in notes:
        clean = clean_health_check(note, end_day)
        if clean is None:
            continue
        grouped.setdefault(normalize_name(clean.name), []).append(clean)
    return {
        name: tuple(
            sorted(
                items,
                key=lambda item: (item.checked_at is not None, item.checked_at or date.min),
                reverse=True,
            )[:MAX_HEALTH_CHECKS_PER_PERSON]
        )
        for name, items in grouped.items()
    }


def has_health_check_risk(note: HealthCheckNote) -> bool:
    return bool(HEALTH_CHECK_RISK_LABELS.intersection(note.labels))


def in_health_check_context(note: HealthCheckNote, comparison_start: datetime, end: datetime) -> bool:
    return note.checked_at is not None and comparison_start.date() <= note.checked_at <= end.date()


def build(payload: PrepareInput) -> PreparedReport:
    cohort = normalize_cohort(payload.cohort)
    operation_all = cohort_rows(payload.operation_rows, cohort)
    previous_rows = deduplicate(
        tuple(row for row in operation_all if in_window(submitted_at(value(row, 5)), payload.comparison_start, payload.start)),
        1,
        5,
    )
    current_rows = deduplicate(
        tuple(row for row in operation_all if in_window(submitted_at(value(row, 5)), payload.start, payload.end)),
        1,
        5,
    )
    previous_operation = operation_period(previous_rows, payload.operation_dashboard_rows, cohort)
    current_operation = operation_period(current_rows, payload.operation_dashboard_rows, cohort)
    general = operation_voc(current_rows)
    learning_all = cohort_rows(payload.learning_rows, cohort)
    previous_bundles = learning_surveys(learning_all, payload.comparison_start, payload.start, payload.learning_dashboard_rows, cohort)
    current_bundles = learning_surveys(learning_all, payload.start, payload.end, payload.learning_dashboard_rows, cohort)
    previous_learning = tuple(summary for summary, _ in previous_bundles)
    learning = tuple(summary for summary, _ in current_bundles)
    roster = active_roster(payload.roster_rows, payload.roster_cohort_label, payload.roster_excluded_names)
    missing: list[MissingResponseGroup] = []
    if current_rows:
        missing.append(MissingResponseGroup(survey="운영 만족도", subject=None, names=missing_names(roster, current_rows)))
    for summary, rows in current_bundles:
        missing.append(MissingResponseGroup(survey="학습 만족도", subject=summary.subject, names=missing_names(roster, rows)))

    health_checks = health_check_index(payload.health_check_notes, payload.end.date())
    issue_data: dict[str, dict[str, Any]] = {}

    def issue_entry(raw_name: object) -> dict[str, Any] | None:
        displayed = str(raw_name or "").strip()
        normalized = normalize_name(displayed)
        if not normalized:
            return None
        return issue_data.setdefault(
            normalized,
            {"name": displayed, "operation": None, "learning": [], "health": ()},
        )

    for row in current_rows:
        operation_score = score(value(row, 2))
        if operation_score <= 3:
            entry = issue_entry(value(row, 1))
            if entry is not None:
                entry["operation"] = operation_score
    for survey, subject_rows in current_bundles:
        for row in subject_rows:
            scores = (score(value(row, 3)), score(value(row, 4)), score(value(row, 6)))
            if min(scores) <= 3:
                entry = issue_entry(value(row, 1))
                if entry is None:
                    continue
                learning_scores = entry["learning"]
                if isinstance(learning_scores, list):
                    learning_scores.append(
                        LearningScore(
                            subject=survey.subject,
                            content=scores[0],
                            live=scores[1],
                            assignment=scores[2],
                            original=valid_voc(value(row, 8)),
                        )
                    )
    for normalized, notes in health_checks.items():
        if any(has_health_check_risk(note) and in_health_check_context(note, payload.comparison_start, payload.end) for note in notes):
            entry = issue_entry(notes[0].name)
            if entry is not None:
                entry["health"] = notes
    for normalized, entry in issue_data.items():
        if not entry["health"] and normalized in health_checks:
            entry["health"] = health_checks[normalized]
    special_issues = tuple(
        SpecialIssue(
            name=str(data["name"]),
            operation_score=data["operation"] if isinstance(data["operation"], int) else None,
            learning_scores=tuple(data["learning"]) if isinstance(data["learning"], list) else (),
            health_checks=tuple(data["health"]) if isinstance(data["health"], tuple) else (),
        )
        for data in issue_data.values()
    )
    originals = tuple(item.original for item in general) + tuple(item.original for survey in learning for item in survey.voc)
    long_originals = tuple(
        item for item in originals if len(item) >= 300 or len(tuple(line for line in item.splitlines() if line.strip())) >= 4
    )
    roster_count_label = "마스터시트 훈련중(내부 제외 반영)" if payload.roster_excluded_names else "마스터시트 훈련중"
    warnings = source_warnings(roster, current_operation, learning, roster_count_label)
    missing_people = tuple(name for group in missing for name in group.names)
    return PreparedReport(
        operation=OperationSummary(previous=previous_operation, current=current_operation, general_voc=general, level_classes=()),
        previous_learning=previous_learning,
        learning=learning,
        special_issues=special_issues,
        missing_responses=tuple(missing),
        source_warnings=warnings,
        validation=ValidationContract(
            required_originals=originals,
            long_originals=long_originals,
            special_issue_names=tuple(item.name for item in special_issues),
            operation_voc_required=bool(current_rows),
            level_classes=(),
            learning_subjects=tuple(item.subject for item in learning),
            dashboard_required=bool(learning),
            missing_response_names=missing_people,
            missing_response_required=bool(missing),
            source_warning_required=bool(warnings),
        ),
    )


def main() -> None:
    payload = PrepareInput.model_validate_json(sys.stdin.read())
    _ = sys.stdout.write(build(payload).model_dump_json())
    _ = sys.stdout.write("\n")


if __name__ == "__main__":
    main()
