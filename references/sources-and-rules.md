# Sources and rules

## Source allowlist

Treat all sources as read-only. Read only the URLs and tab names saved in the local profile and confirm metadata before every live run.

### Satisfaction workbook

Use the configured satisfaction dashboard workbook.

- Profile `sheets.dashboard`
  - Learning table `A:J`: cohort, subject, survey date, current count, response count, response rate, content, live, assignment, achievement.
  - Operation table `L:R`: week, cohort, survey date, current count, response count, response rate, operation score.
- Profile `sheets.learning` approved range `A:M`
  - A cohort, B name, C subject, D content score, E live score, F difficulty (unused), G assignment score, H understanding (unused), I VOC, J-K metadata, L submitted timestamp, M token.
- Profile `sheets.operation` approved range `A:G`
  - A cohort, B name, C operation score, D score reason, E other opinion, F submitted timestamp, G token.

### Roster workbook

Use the configured roster workbook and profile `sheets.roster` tab, approved range `A:E` only.

- A camp/cohort label, C name, E trainee status.
- Include only rows whose A value exactly matches `roster_cohort_label` after whitespace normalization and whose E value is exactly `훈련중`.
- Exclude names listed in profile `roster_excluded_names` after whitespace normalization.
- Never read or retain birth date, phone, email, address, payment, equipment, or other personal columns.

### Notion health check

When `health_check_data_source_url` is configured, use only that Notion data source.

Approved properties:

- `수강생 이름`: title/name.
- `기수`: must exactly equal profile `roster_cohort_label`.
- `상담일`: use `date:상담일:start`.
- `차수`: counseling cycle such as `1차`, `2차`, or `비정규상담`.
- `라벨`: multi-select labels.
- Row URL and page body only for selected risk candidates.

Do not write, move, update, archive, or comment on health-check records.

## Assignment isolation

- Normalize only superficial cohort formatting such as `5`, `5기`, or numeric 5 in the satisfaction workbook.
- Search only the cohort column before fetching rows.
- Match the roster with the exact profile `roster_cohort_label`.
- Pass every fetched row to `prepare-report-data.py`; its second exact check is authoritative.
- Never include another cohort's name, VOC, metrics, or roster data.

## Deduplication and metrics

- Operation key: cohort + normalized respondent name within one operation dashboard survey period. Use the latest dashboard survey date on or before the report cutoff as the current survey. Include raw operation responses from that date 00:00 through the report cutoff, and keep the latest F timestamp per respondent.
- Previous operation metrics use the immediately preceding dashboard survey date and include raw operation responses from that date 00:00 until before the current survey date 00:00.
- Learning key: cohort + exact subject + normalized respondent name. Keep the latest L timestamp.
- Operation score: arithmetic mean of valid C scores.
- Content, live, and assignment: arithmetic means of D, E, and G.
- Achievement: mean of the three unrounded subject means.
- Round only final display values to one decimal using half-up rounding.
- Use deduplicated response counts from raw tabs. Use the dashboard only for current-count and response-count cross-checks.
- Match a learning dashboard row by cohort and exact subject, choosing the closest dashboard survey date within seven days because scheduled dates may precede the response wave.
- Display operation satisfaction as `score (deduplicated responses/dashboard current count)`.

## New learning survey

For each exact subject in the current window:

1. Deduplicate its assigned-cohort history through the cutoff.
2. Treat it as new when no earlier valid response exists.
3. Also treat it as new when all pre-open exception conditions hold: at most three earlier respondents, at least five current respondents, at least five responses on one current-window date, and current respondents are at least 70% of all respondents through cutoff.
4. For a normal first response, aggregate the current window. For the exception, aggregate isolated earlier responses plus current responses.
5. Once a subject has been reported, ignore later responses in every section.

## Missing respondents

- Compare each current survey's deduplicated normalized respondent names with the exact `훈련중` roster after profile `roster_excluded_names`.
- Produce a separate list for operation satisfaction and for each new learning subject.
- Preserve roster display names in the report.
- Never infer active enrollment from historical responders.
- When roster count and dashboard current count differ, still calculate from the roster but add a `데이터 확인 필요` warning.
- When dashboard response count and raw deduplicated count differ, use the raw count and add a warning.
- If the roster cannot be proven, do not guess a missing-person list; fail the report.

## VOC rules

- D and E from profile `sheets.operation` are both general operation VOC.
- I from profile `sheets.learning` is learning VOC for that exact subject.
- Ignore blanks and non-opinions such as `없음`, `없습니다`, `없어요`, `따로 없습니다`, and punctuation-only values.
- Include every valid positive opinion and every improvement, request, concern, or low-score explanation.
- Classify by the response's final meaning. An unresolved request or problem is improvement; a resolved difficulty or personal review plan without an operator request is positive.
- Scores are metadata and special-issue signals, not VOC classification rules.
- Preserve each original exactly, including spelling, spacing, punctuation, emoji, and line breaks.
- For responses of at least 300 characters or four non-empty lines, add one source-bounded summary and retain the full original under `원문 보기`.
- Add respondent name and scores to improvement labels, never inside the original text.
- Do not emit raw HTML.

Read `report-decision-examples.md` before classifying VOC.

## Special issues

Include only assigned-cohort people with one of these grounds:

- A manual issue note explicitly supplied in the current conversation.
- Operation or any learning score is 3: counseling-review candidate.
- Operation or any learning score is 2 or below: important-review candidate.
- A Notion health-check note in the comparison/current report context has a risk label: `불만`, `학습고민`, `독려`, `강성`, `이슈상담`, `진로상담`, `하차예정`, `하차`, `관심이 필요함`, `수강철회`, `출결문의`, `회피형`, `소심함`, `고민`, `😣`, or `🤐`.

For health-check notes:

- Consider notes whose `상담일` is between `comparison_start` and the report `end`, inclusive.
- If a person is already a special-issue candidate from satisfaction scores, attach that person's latest health-check note up to the report `end` even if the note is older than `comparison_start`.
- Use the note's `상담일`, `차수`, `라벨`, and compact 상담 내용 facts as source facts.
- Treat explicit 상담 대응, 안내, 결과, 하차방어완료, or 유사 follow-up content as confirmed operator response facts. Do not invent follow-up status.

Merge all grounds by normalized respondent name. Use source facts only. When no source-backed operator response exists, render `확인된 운영진 대응 내용 없음(수기 보완 필요)`.

## Scheduling

- For `schedule_mode: weekly_monday`, run weekly on Monday at profile `schedule_time` and use duplicate-window protection.
- For `schedule_mode: first_business_day`, calculate Korean public holidays with `holidays.KR`, add profile `extra_holidays`, schedule on weekdays at profile `schedule_time`, and continue only on that week's first non-weekend, non-holiday date.
- A Monday public holiday therefore moves `first_business_day` mode to Tuesday; consecutive holidays move it to the next business day.

## Failure conditions

Stop without a partial report or state update when access, metadata, headers, cohort filtering, truncation, roster matching, parsing, calculation, rendering, or validation cannot be proven.
