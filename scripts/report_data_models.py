from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import ClassVar, Final, TypeAlias

from pydantic import BaseModel, ConfigDict

Cell: TypeAlias = str | int | float | None
Row: TypeAlias = tuple[Cell, ...]
SEOUL: Final = timezone(timedelta(hours=9))
SHEET_EPOCH: Final = datetime(1899, 12, 30, tzinfo=SEOUL)
ONE_DECIMAL: Final = Decimal("0.1")
LEVEL_ORDER: Final = ("새싹반", "열정반", "심화반")
FILLERS: Final = frozenset(
    {
        "없음",
        "없습니다",
        "없어요",
        "없다",
        "없습니당",
        "업습니다",
        "따로 없습니다",
        "x",
        "ㅎ",
    }
)


class PrepareInput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    cohort: str
    comparison_start: datetime
    start: datetime
    end: datetime
    operation_rows: tuple[Row, ...]
    learning_rows: tuple[Row, ...]
    learning_dashboard_rows: tuple[Row, ...]
    operation_dashboard_rows: tuple[Row, ...]
    roster_rows: tuple[Row, ...]
    roster_cohort_label: str
    roster_excluded_names: tuple[str, ...] = ()
    health_check_notes: tuple["HealthCheckNote", ...] = ()


class VocItem(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    name: str
    original: str
    score_label: str
    source_field: str


class LevelClassVoc(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    name: str
    voc: tuple[VocItem, ...]


class MetricSummary(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    content: str
    live: str
    assignment: str
    achievement: str
    respondent_count: int
    current_count: int | None
    dashboard_response_count: int | None


class OperationPeriod(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    score: str | None
    respondent_count: int
    survey_date: date | None
    current_count: int | None
    dashboard_response_count: int | None


class OperationSummary(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    previous: OperationPeriod
    current: OperationPeriod
    general_voc: tuple[VocItem, ...]
    level_classes: tuple[LevelClassVoc, ...]


class LearningSummary(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    subject: str
    survey_date: date
    metrics: MetricSummary
    voc: tuple[VocItem, ...]


class LearningScore(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    subject: str
    content: int
    live: int
    assignment: int
    original: str | None


class HealthCheckNote(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    name: str
    checked_at: date | None = None
    cycle: str | None = None
    labels: tuple[str, ...] = ()
    note: str | None = None
    url: str | None = None


class SpecialIssue(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    name: str
    operation_score: int | None
    learning_scores: tuple[LearningScore, ...]
    health_checks: tuple[HealthCheckNote, ...] = ()


class ValidationContract(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    required_originals: tuple[str, ...]
    long_originals: tuple[str, ...]
    special_issue_names: tuple[str, ...]
    operation_voc_required: bool
    level_classes: tuple[str, ...]
    learning_subjects: tuple[str, ...]
    dashboard_required: bool
    missing_response_names: tuple[str, ...]
    missing_response_required: bool
    source_warning_required: bool


class MissingResponseGroup(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    survey: str
    subject: str | None
    names: tuple[str, ...]


class PreparedReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    operation: OperationSummary
    previous_learning: tuple[LearningSummary, ...]
    learning: tuple[LearningSummary, ...]
    special_issues: tuple[SpecialIssue, ...]
    missing_responses: tuple[MissingResponseGroup, ...]
    source_warnings: tuple[str, ...]
    validation: ValidationContract
