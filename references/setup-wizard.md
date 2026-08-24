# Setup wizard

Use this reference when the user asks to install, configure, or schedule the weekly report skill, or when `scripts/check-profile.py --init-missing` returns `needs_setup`.

## Goal

Make setup feel like: install the skill, then tell Codex the 담당 캠프 and 기수. Derive everything else from presets and connected Google Drive/Notion where it can be verified. Ask the user only for values that cannot be discovered safely.

## Preset-first setup

Run:

```bash
python3 ABSOLUTE_SKILL_PATH/scripts/check-profile.py --init-missing
```

If `setup_stage` is `cohort_selection`, ask one concise question:

```text
담당 캠프와 기수를 알려주세요. 예: 창업가 5기 / 디자이너 3기
```

When the user answers, normalize numeric cohorts to `N기` and save the values with:

```bash
python3 ABSOLUTE_SKILL_PATH/scripts/check-profile.py --init-missing --set "camp=캠프명" --set "cohort=N기"
```

Known camp presets:

- 창업가: report/roster label `창업가 N기`; tabs `창업가 대시보드`, `창업가 학습`, `창업가 운영`, `창업가_수강생 주요 정보`.
- 디자이너: report/roster label `디자이너 N기`; tabs `디자이너 대시보드`, `디자이너 학습`, `디자이너 운영`, `디자이너_수강생 주요 정보`.

For an unknown camp, keep the user's camp name for `report_label` and `roster_cohort_label`, then ask for the four tab names only if metadata validation cannot derive them.

## Source discovery

If `setup_stage` is `source_discovery`, use the connected Google Drive connector in read-only mode.

1. Search for a Google Sheets file matching `setup_hints.drive_search.satisfaction_dashboard_query`, usually `[교육팀] 만족도 대시보드`.
2. Prefer the exact-title spreadsheet that contains the expected dashboard, learning, and operation tabs.
3. Search for a Google Sheets file matching `setup_hints.drive_search.roster_query`, usually `마스터시트`.
4. Prefer the spreadsheet that contains the expected roster tab and whose roster A column has the exact `roster_cohort_label`.
5. If exactly one safe candidate is found for each source, save the URLs:

```bash
python3 ABSOLUTE_SKILL_PATH/scripts/check-profile.py --init-missing --set "satisfaction_dashboard_url=URL" --set "roster_url=URL"
```

Ask the user to choose or paste a URL only when there are zero candidates, multiple plausible candidates, missing expected tabs, or connector access is unavailable.

During discovery, do not read satisfaction response rows, VOC, respondent names, tokens, or roster columns beyond the bounded metadata/header/cohort checks needed to identify the correct files.

## Optional Notion output

If the user provides a Notion parent page URL, save it:

```bash
python3 ABSOLUTE_SKILL_PATH/scripts/check-profile.py --init-missing --set "notion_parent_url=URL"
```

If the user provides a health-check data source URL, save it:

```bash
python3 ABSOLUTE_SKILL_PATH/scripts/check-profile.py --init-missing --set "health_check_data_source_url=URL"
```

Do not block setup on Notion fields. If `notion_parent_url` is blank, return validated reports in chat instead of creating Notion pages.

## Ready state

After every setup change, rerun:

```bash
python3 ABSOLUTE_SKILL_PATH/scripts/check-profile.py --init-missing
```

When it returns `ready`, summarize the resolved camp, cohort, sheet tabs, source file names/URLs, Notion output status, and Monday 10:30 Asia/Seoul schedule. Then run one manual report before registering the recurring automation.

Only after a manual report succeeds, create or update one recurring Codex automation named `{report_label} 만족도 주간보고`. Reuse an existing automation with the same name.
