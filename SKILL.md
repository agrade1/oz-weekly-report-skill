---
name: oz-weekly-report
description: Create and schedule OZ Coding School bootcamp weekly satisfaction reports from configured Google Sheets, roster data, and optional Notion health-check data. Use for cohort-specific satisfaction metrics, VOC preservation, missing respondent lists, low-score issues, Notion output, and report automation setup.
---

# OZ Weekly Satisfaction Report

Prepare a weekly satisfaction report for the configured OZ bootcamp cohort. The cohort, source spreadsheets, tab names, roster label, excluded roster names, Notion output location, and schedule are all user-specific settings stored in a local profile. Keep source Google Sheets and Notion health-check records strictly read-only.

## Required Resources

Before reading source data, read:

1. `references/sources-and-rules.md`
2. `references/source-read-orchestration.md`

After preprocessing, read:

1. `references/report-decision-examples.md`
2. `references/report-render-orchestration.md`

Use scripts in this order:

1. `scripts/check-profile.py`
2. `scripts/report-window.py`
3. `scripts/prepare-report-data.py`
4. `scripts/render-report.mjs`
5. `scripts/validate-report.py`

Pass raw source rows only through standard input. Never save source rows, names, VOC, response tokens, or intermediate manifests to files.

## Setup Gate

Use profile `~/.codex/oz-weekly-report/profile.yaml` and state `~/.codex/oz-weekly-report/state.yaml`.

At the start of every run, execute `scripts/check-profile.py --init-missing`. If it returns `needs_setup`, stop before reading Google Sheets or Notion and show a concise setup prompt using `setup_prompts` and the clickable profile path. Ask the user to provide the missing settings in chat or edit the profile. Do not register automation or create a report until the profile is `ready`.

Profile template:

```yaml
version: 3

camp:
# 예: 1인 창업가
cohort:
# 예: 5기
cohort_query:
# 예: 5
report_label:
# 예: 창업가 5기. 비워두면 "<camp> <cohort>"로 계산
roster_cohort_label:
# 예: 창업가 5기. 마스터시트 A열 및 헬스체크 기수명과 정확히 일치해야 함
roster_excluded_names: []
# 예: [홍길동, 김오즈]. 원본 시트는 수정하지 않고 내부 재원 기준에서 제외

satisfaction_dashboard_url:
roster_url:

sheets:
  dashboard: 창업가 대시보드
  learning: 창업가 학습
  operation: 창업가 운영
  roster: 창업가_수강생 주요 정보

notion_parent_url:
health_check_page_url:
health_check_data_source_url:

timezone: Asia/Seoul
schedule_mode: weekly_monday
# weekly_monday 또는 first_business_day
schedule_time: "10:30"
extra_holidays: []
```

Required settings are `camp`, `cohort`, `cohort_query`, `report_label`, `roster_cohort_label`, `satisfaction_dashboard_url`, `roster_url`, `sheets.dashboard`, `sheets.learning`, `sheets.operation`, `sheets.roster`, `timezone`, `schedule_mode`, and `schedule_time`. Notion output and health-check settings are optional.

## Source Safety

- Require the connected Google Drive spreadsheet connector.
- When `health_check_data_source_url` is configured, require the connected Notion connector.
- Read only the configured satisfaction workbook, roster workbook, and optional Notion health-check data source.
- Read only the configured `sheets.dashboard`, `sheets.learning`, `sheets.operation`, and `sheets.roster` tabs.
- Use metadata, bounded header reads, cohort-only searches, and bounded matching-row reads.
- Never call Drive, Docs, Sheets, or spreadsheet write/update/create/copy/append/batch-update actions.
- Never read roster columns beyond `A:E`.
- Stop on access, schema, truncation, cohort, roster, calculation, rendering, or validation uncertainty.

## Source Validation

After the profile is ready:

1. Resolve both workbook URLs with metadata.
2. Confirm the satisfaction workbook has the configured dashboard, learning, and operation tabs.
3. Confirm the roster workbook has the configured roster tab.
4. Read only these header ranges once, using configured tab names:
   - dashboard tab `A1:R1`
   - learning tab `A1:M1`
   - operation tab `A1:G1`
   - roster tab `A2:E2`
5. Require the headers and column meanings in `references/sources-and-rules.md`.

Do not use public CSV export fallback. The active roster is private and required for the missing-respondent list.

## Run Window

For manual invocations, call `report-window.py` with `scheduled_run: false` and generate the latest completed weekly window immediately.

For automations:

- If `schedule_mode` is `weekly_monday`, schedule the automation on Monday at `schedule_time` in `timezone`, call `report-window.py` with `scheduled_run: false`, and skip only when the computed window is already covered by `state.yaml`.
- If `schedule_mode` is `first_business_day`, schedule the automation on weekdays at `schedule_time` in `timezone`, call `report-window.py` with `scheduled_run: true`, and stop when `should_run` is false.

Read `last_successful_report_at` from state when present. On replay, regenerate the same completed window. Update state to the window `end` only after final report validation and, when configured, successful Notion creation.

## Cohort-Only Read And Preprocessing

Run the exact orchestration in `references/source-read-orchestration.md`.

- Search `cohort_query` only in the cohort column before fetching satisfaction rows.
- Search exact `roster_cohort_label` only in roster column A before fetching roster rows.
- Apply `roster_excluded_names` inside preprocessing; do not edit the source roster sheet.
- If `health_check_data_source_url` is configured, query only that Notion data source for exact `roster_cohort_label` rows and fetch detail pages only for risk-label candidates.
- Confirm no search result is truncated.
- Fetch only matching rows and approved columns.
- Let `prepare-report-data.py` perform exact cohort checks, deduplication, survey detection, metrics, roster comparison, missing respondents, source consistency warnings, VOC routing, and low-score/health-check special issues.

Never expose raw source rows or the roster to model context. The orchestration returns only compact VOC and special-issue decision data.

## Classification And Rendering

For every returned VOC ID, decide exactly one category: `positive` or `improvement`. Add a source-bounded summary only when `long` is true. For every special-issue person, provide one title, source-backed situation facts, and only confirmed response facts. Use `health_checks` facts when present, including 상담일, 차수, 라벨, and 상담 본문 excerpts.

Run the exact block in `references/report-render-orchestration.md`. Do not manually assemble or edit report Markdown. If validation fails, correct only compact decisions and retry once. After a second failure, output:

```text
주간보고 생성 실패: 최종 보고서 완전성 검증
```

## Report Contents

Render in this order:

1. Quantitative report for previous and current periods.
2. Missing respondents by operation survey and each new learning subject.
3. Dashboard-vs-roster and dashboard-vs-raw count warnings when present.
4. Special issues when present.
5. Operation VOC.
6. Learning VOC for each new subject.
7. Dashboard-entry table for each new learning subject.

The missing-person list is based on the `훈련중` roster after applying `roster_excluded_names`, not historical responders. When the roster count differs from dashboard current count, keep the roster-based list and render the discrepancy warning.

## Notion Delivery

If `notion_parent_url` is blank, return the validated Writing block only.

If `notion_parent_url` is configured:

1. Create one child page under that exact parent.
2. Title it `{report_label} 주간 만족도 보고서 YYYY-MM-DD`.
3. Remove only the outer Writing wrapper before passing the validated Markdown body to Notion.
4. Preserve headings, tables, nested lists, VOC originals, special issues, missing respondents, and warnings.
5. Verify the created page by reading it back.
6. Return the validated report and the observed Notion page URL.

Never guess a Notion parent or overwrite an existing page. On a same-window replay, reuse the page identified in state when available rather than creating a duplicate.

## Automation Registration

After the profile is ready and one manual report succeeds, create or update one recurring Codex automation named `{report_label} 만족도 주간보고`.

- Use `schedule_mode`, `schedule_time`, and `timezone` from profile.
- Prompt: invoke `$oz-weekly-report` as a scheduled run, read profile and state, apply duplicate-window protection, create the validated report, include the missing-respondent list, create the configured Notion page, and update state only after success.
- Reuse an exact-name automation instead of creating duplicates.

Do not register automation during installation or source validation.

## Failure Output

For source or calculation failures, output one line only:

```text
주간보고 생성 실패: <확인이 필요한 항목>
```

Do not emit a partial report and do not update state.
