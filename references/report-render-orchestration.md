# Deterministic report rendering

After receiving the decision view, classify each `voc_items` entry exactly once. Do not write Markdown. Build only this compact decision object in memory:

```json
{
  "writing_id": "12345",
  "voc_decisions": [
    {"id": "voc-001", "category": "positive"},
    {"id": "voc-002", "category": "improvement", "summary": "긴 의견의 미해결 문제 요약"}
  ],
  "issue_decisions": [
    {
      "name": "이름",
      "title": "학습 부진 (과목명 만족도 2점)",
      "situation": ["원천에서 확인된 사실."],
      "responses": []
    }
  ]
}
```

- Use `summary` only when the decision view has `long: true`; it is required for every such item.
- Use `positive` or `improvement` according to `report-decision-examples.md`.
- Include every VOC ID once. Never include the original text in the decision object.
- Include every special-issue name once. Leave `responses` empty when no source-backed response exists; the renderer inserts the fixed manual-completion notice.
- Never use `검토` as the issue title.
- When a `special_issues` item includes `health_checks`, use those facts in `situation`: 상담일, 차수, 라벨, and compact 상담 본문 facts. Put 상담 대응/안내/결과 facts in `responses` only when explicitly source-backed.

Then run one `functions.exec` call with this pattern. Fill the paths and `decisions` constant only:

```javascript
const manifest = load("oz_weekly_manifest");
if (!manifest) throw new Error("report manifest unavailable");
const renderer = ABSOLUTE_RENDER_REPORT_PATH;
const validator = ABSOLUTE_VALIDATE_REPORT_PATH;
const decisions = REPORT_DECISION_OBJECT;
const shellQuote = value => `'${value.replaceAll("'", "'\"'\"'")}'`;
const renderPayload = JSON.stringify({...decisions, manifest});
const rendered = await tools.exec_command({
  cmd: `printf '%s' ${shellQuote(renderPayload)} | node ${shellQuote(renderer)}`,
  yield_time_ms: 30000,
  max_output_tokens: 30000,
});
if (rendered.exit_code !== 0) throw new Error("deterministic report rendering failed");
const report = rendered.output.trimEnd();
const specialIssueNames = [...new Set([
  ...manifest.validation.special_issue_names,
  ...decisions.issue_decisions.map(item => item.name),
])];
const validationPayload = JSON.stringify({
  report,
  ...manifest.validation,
  special_issue_names: specialIssueNames,
});
const validated = await tools.exec_command({
  cmd: `printf '%s' ${shellQuote(validationPayload)} | python3 -m uv run --quiet ${shellQuote(validator)}`,
  yield_time_ms: 30000,
  max_output_tokens: 3000,
});
if (validated.exit_code !== 0 || validated.output.trim() !== '{"valid":true}') {
  throw new Error("final report validation failed");
}
text(report);
```

Do not manually edit the rendered Markdown. If rendering or validation fails, correct only the compact decision object and run this block once more with the stored manifest.
