# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pydantic>=2.11,<3",
#   "pytest>=8.4,<9",
# ]
# ///
# ─── How to run ───
# uv run test-validate-report.py

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest

VALIDATOR: Final = Path(__file__).with_name("validate-report.py")


def run_validator(report: str) -> subprocess.CompletedProcess[str]:
    payload = {
        "report": report,
        "required_originals": ["운영 원문", "학습 원문"],
        "long_originals": ["학습 원문"],
        "special_issue_names": ["윤채은"],
        "operation_voc_required": True,
        "level_classes": ["새싹반"],
        "learning_subjects": ["UI 디자인 실무"],
        "dashboard_required": True,
        "missing_response_names": ["김미응답"],
        "missing_response_required": True,
        "source_warning_required": True,
    }
    return subprocess.run(
        [sys.executable, str(VALIDATOR)],
        input=json.dumps(payload),
        check=False,
        capture_output=True,
        text=True,
    )


def test_rejects_partial_report_before_state_can_be_updated() -> None:
    report = """:::writing{variant="document" id="12345"}
## 정량 보고
## 미응답 수강생
- **운영 만족도 (1명)**: 김미응답
- **데이터 확인 필요**
  - 대시보드와 명단 인원 불일치
## 📊 08/07 학만조 VOC _UI 디자인 실무
- 학습 원문
## 특이사항
- **윤채은 — 학습 부진**
## 운영 대시보드 입력용
:::"""

    completed = run_validator(report)

    assert completed.returncode != 0
    assert "운만조 VOC" in completed.stderr
    assert "운영 원문" in completed.stderr


def test_accepts_complete_report_in_fixed_section_order() -> None:
    report = """:::writing{variant="document" id="12345"}
## 정량 보고
## 미응답 수강생
- **운영 만족도 (1명)**: 김미응답
- **데이터 확인 필요**
  - 대시보드와 명단 인원 불일치
## 특이사항
- **윤채은 — 학습 부진**

  `상황`

  - 과제 수행에 어려움을 느꼈고 과제 만족도 2점이 확인됨.

  `운영진 대응 및 결과`

  - 확인된 운영진 대응 내용 없음(수기 보완 필요)
## 📊 08/07 운만조 VOC 요약
- 운영 원문
#### 수준별 학습반
- **새싹반**
## 📊 08/07 학만조 VOC _UI 디자인 실무
- 학습 문제 요약
  - 원문 보기
    - 학습 원문
## 운영 대시보드 입력용
:::"""

    completed = run_validator(report)

    assert completed.returncode == 0
    assert json.loads(completed.stdout) == {"valid": True}


def test_rejects_generic_or_empty_special_issue() -> None:
    report = """:::writing{variant="document" id="12345"}
## 정량 보고
## 미응답 수강생
- **운영 만족도 (1명)**: 김미응답
- **데이터 확인 필요**
  - 대시보드와 명단 인원 불일치
## 특이사항
- **윤채은 — UI 디자인 실무 학습 만족도 검토**

  `상황`

  - UI 디자인 실무 학습 만족도 검토

  `운영진 대응 및 결과`

  -
## 📊 08/07 운만조 VOC 요약
- 운영 원문
#### 수준별 학습반
- **새싹반**
## 📊 08/07 학만조 VOC _UI 디자인 실무
- 학습 문제 요약
  - 원문 보기
    - 학습 원문
## 운영 대시보드 입력용
:::"""

    completed = run_validator(report)

    assert completed.returncode != 0
    assert "문제 제목이 구체적이지 않음" in completed.stderr
    assert "대응 내용 누락" in completed.stderr


def test_accepts_short_original_that_also_appears_inside_another_original() -> None:
    payload = {
        "report": """:::writing{variant="document" id="12345"}
## 정량 보고
## 📊 08/07 운만조 VOC 요약
- 좋아요
- 수업이 좋아요
:::""",
        "required_originals": ["좋아요", "수업이 좋아요"],
        "long_originals": [],
        "special_issue_names": [],
        "operation_voc_required": True,
        "level_classes": [],
        "learning_subjects": [],
        "dashboard_required": False,
        "missing_response_names": [],
        "missing_response_required": False,
        "source_warning_required": False,
    }
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        input=json.dumps(payload),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
