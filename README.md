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

## 공유용 안내문

**[OZ 부트캠프 만족도 조사 자동화 Skill 안내]**

안녕하세요. 조교님들의 업무 효율성을 높이고 수강생 의견 누락을 줄이기 위해 주간 만족도 조사 자동화 Skill을 준비했습니다.

**[준비물]**

- [Codex Desktop](https://openai.com/ko-KR/codex/)
- Google 계정 연결
- Notion에 보고서를 만들 경우 Notion 계정 연결

**[설치방법]**

1. Codex에 Google 계정을 연동합니다. ([참고링크](https://help.openai.com/ko-kr/articles/10948259-google-drive-app-with-sync-self-service-setup))
2. Codex 채팅에 아래 문장을 붙여넣습니다.

```text
아래 GitHub 스킬을 설치하고, 설치가 끝나면 다음 턴에서 설정을 진행하라고 안내해줘.
https://github.com/agrade1/oz-weekly-report-skill
```

3. 설치가 끝나면 Codex 채팅에 담당 캠프와 기수를 알려줍니다.

```text
$oz-weekly-report 설정해줘. 담당 캠프는 디자이너, 기수는 5기야.
```

Codex가 연결된 Google Drive에서 기본 만족도 대시보드와 마스터시트를 찾고, 필요한 값이 부족할 때만 추가로 질문합니다.

**[기대효과]**

- 주간 만족도 지표, 전체 유효 VOC, 저점자 특이사항, 미응답 수강생 리스트를 자동으로 정리합니다.
- 매주 월요일 10시 기준 자동 실행되도록 설정할 수 있습니다.
- 원본 Google Sheets와 Notion 헬스체크 데이터는 읽기 전용으로만 조회합니다.

## Install With Codex

Recommended flow: ask Codex to install the skill instead of typing the installer command yourself.

Paste this into a Codex chat:

```text
아래 GitHub 스킬을 설치하고, 설치가 끝나면 다음 턴에서 설정을 진행하라고 안내해줘.
https://github.com/agrade1/oz-weekly-report-skill
```

After Codex says the skill is installed, start setup in the Codex chat:

```text
$oz-weekly-report 설정해줘. 담당 캠프는 창업가, 기수는 5기야.
```

Do not type `$oz-weekly-report 설정해줘` in a terminal. It is a Codex chat prompt, not a shell command.

## Manual Install

If this repository root is the skill folder:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo agrade1/oz-weekly-report-skill --path . --name oz-weekly-report --ref main --method download
```

If this folder is published under `skills/oz-weekly-report`:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo agrade1/oz-weekly-report-skill --path skills/oz-weekly-report --ref main --method download
```

## First Run Setup

Run the skill in Codex with the camp and cohort:

```text
$oz-weekly-report 설정해줘. 담당 캠프는 디자이너, 기수는 5기야.
```

The skill creates or checks:

```text
~/.codex/oz-weekly-report/profile.yaml
```

If required settings are missing, Codex stops before reading report rows and asks only for the current setup stage's missing values. For known camp presets such as `창업가` and `디자이너`, Codex derives report labels, roster labels, tab names, timezone, and the Monday 10:00 schedule.

Required settings:

- `camp`: course name, for example `창업가` or `디자이너`
- `cohort`: displayed cohort, for example `5기`
- `satisfaction_dashboard_url`: Google Sheets URL for the satisfaction dashboard
- `roster_url`: Google Sheets URL for the roster/master sheet

Derived for known camp presets:

- `cohort_query`: value used in satisfaction sheet cohort columns, for example `5`
- `report_label`: report title label, for example `창업가 5기`
- `roster_cohort_label`: exact roster/health-check cohort label, for example `창업가 5기`
- `sheets.dashboard`, `sheets.learning`, `sheets.operation`, `sheets.roster`
- `timezone`, `schedule_mode`, `schedule_time`

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
