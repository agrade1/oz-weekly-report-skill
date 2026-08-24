# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pydantic>=2.11,<3",
# ]
# ///
# ─── How to run ───
# printf '%s' '{"content":[4,5],"live":[5,4],"assignment":[4,4],"respondent_count":2}' \
#   | uv run aggregate-metrics.py

from __future__ import annotations

import sys
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

ONE_DECIMAL: Final = Decimal("0.1")
NonEmptyScores = Annotated[tuple[Decimal, ...], Field(min_length=1)]


class MetricInput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    content: NonEmptyScores
    live: NonEmptyScores
    assignment: NonEmptyScores
    respondent_count: PositiveInt


class MetricResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    content: str
    live: str
    assignment: str
    achievement: str
    respondent_count: PositiveInt


def mean(scores: NonEmptyScores) -> Decimal:
    return sum(scores, start=Decimal(0)) / Decimal(len(scores))


def display(score: Decimal) -> str:
    return format(score.quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP), ".1f")


def calculate(payload: MetricInput) -> MetricResult:
    content = mean(payload.content)
    live = mean(payload.live)
    assignment = mean(payload.assignment)
    achievement = (content + live + assignment) / Decimal(3)
    return MetricResult(
        content=display(content),
        live=display(live),
        assignment=display(assignment),
        achievement=display(achievement),
        respondent_count=payload.respondent_count,
    )


def main() -> None:
    payload = MetricInput.model_validate_json(sys.stdin.read())
    _ = sys.stdout.write(calculate(payload).model_dump_json())
    _ = sys.stdout.write("\n")


if __name__ == "__main__":
    main()
