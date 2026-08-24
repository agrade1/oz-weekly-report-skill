from __future__ import annotations

import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Final, assert_never

from report_data_models import FILLERS, SEOUL, SHEET_EPOCH, Cell, Row

KOREAN_TIMESTAMP: Final = re.compile(
    r"^(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\s*(오전|오후)\s*(\d{1,2}):(\d{2}):(\d{2})$"
)


class InvalidRowError(ValueError):
    pass


def value(row: Row, index: int) -> Cell:
    return row[index] if index < len(row) else None


def normalize_cohort(raw: Cell) -> str:
    return str(raw).strip().removesuffix("기")


def normalize_name(raw: Cell) -> str:
    return "" if raw is None else "".join(str(raw).split())


def submitted_at(raw: Cell) -> datetime:
    match raw:
        case int() | float():
            return SHEET_EPOCH + timedelta(days=float(raw))
        case str():
            matched = KOREAN_TIMESTAMP.fullmatch(raw.strip())
            if matched is not None:
                year, month, day, period, hour, minute, second = matched.groups()
                hour_value = int(hour) % 12 + (12 if period == "오후" else 0)
                return datetime(
                    int(year), int(month), int(day), hour_value, int(minute), int(second), tzinfo=SEOUL
                )
            parsed = datetime.fromisoformat(raw)
            return parsed.replace(tzinfo=SEOUL) if parsed.tzinfo is None else parsed
        case None:
            raise InvalidRowError("submitted timestamp is missing")
        case unreachable:
            assert_never(unreachable)


def score(raw: Cell) -> int:
    parsed = int(Decimal(str(raw)))
    if not 1 <= parsed <= 5:
        raise InvalidRowError("satisfaction score must be between 1 and 5")
    return parsed


def valid_voc(raw: Cell) -> str | None:
    if raw is None:
        return None
    original = str(raw).strip()
    visible = original.replace("ㅤ", "")
    core = visible.strip(" .,!?:;~-_/\\()[]{}♥♡💗").lower()
    if not core or core in FILLERS or not any(character.isalpha() for character in core):
        return None
    return original
