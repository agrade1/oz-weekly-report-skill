# OZ Weekly Report Skill

OZ Coding School bootcamp satisfaction report skill for Codex.

This skill reads configured Google Sheets and optional Notion health-check data, then creates a validated weekly report with:

- weekly satisfaction metrics
- full valid VOC preservation
- low-score and health-check based special issues
- missing respondent lists
- dashboard/roster consistency warnings
- optional Notion page creation

Source Google Sheets and Notion health-check records are read-only.

## Install

If this repository root is the skill folder:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo OWNER/oz-weekly-report-skill --path . --name oz-weekly-report --ref main --method download
```

If this folder is published under `skills/oz-weekly-report`:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo OWNER/oz-weekly-report-skill --path skills/oz-weekly-report --ref main --method download
```

Replace `OWNER/oz-weekly-report-skill` with the actual GitHub repository.

## First Run Setup

Run the skill in Codex:

```text
$oz-weekly-report 설정해줘
```

The skill creates or checks:

```text
~/.codex/oz-weekly-report/profile.yaml
```

If required settings are missing, Codex stops before reading Sheets/Notion and asks for the missing values.

Required settings:

- `camp`: course name, for example `1인 창업가`
- `cohort`: displayed cohort, for example `5기`
- `cohort_query`: value used in satisfaction sheet cohort columns, for example `5`
- `report_label`: report title label, for example `창업가 5기`
- `roster_cohort_label`: exact roster/health-check cohort label, for example `창업가 5기`
- `satisfaction_dashboard_url`: Google Sheets URL for the satisfaction dashboard
- `roster_url`: Google Sheets URL for the roster/master sheet
- `sheets.dashboard`: dashboard tab name
- `sheets.learning`: learning response tab name
- `sheets.operation`: operation response tab name
- `sheets.roster`: roster tab name
- `timezone`
- `schedule_mode`
- `schedule_time`

Optional settings:

- `roster_excluded_names`: names to exclude internally from roster/missing respondent logic without editing source Sheets
- `notion_parent_url`: parent page for generated weekly reports
- `health_check_page_url`
- `health_check_data_source_url`
- `extra_holidays`

## Schedule Modes

`weekly_monday` runs every Monday at `schedule_time` and skips duplicate report windows.

`first_business_day` runs on weekdays at `schedule_time` and only proceeds on that week's first Korean business day. If Monday is a holiday, Tuesday becomes the run day.

## Development

Run Python tests:

```bash
cd scripts
python3 -m uv run --python 3.12 --with pytest --with pydantic --with pyyaml --with holidays --quiet pytest test-*.py
```

Run Node reference/render tests:

```bash
cd scripts
node test-source-orchestration.mjs
node test-render-report.mjs
node test-public-sheet-source.mjs
```
