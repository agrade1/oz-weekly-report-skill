# Cohort-only source read orchestration

Use one `functions.exec` call for spreadsheet preprocessing so respondent names, raw rows, response tokens, and the roster remain inside the tool isolate. Fill every constant from validated profile values and spreadsheet metadata. Google Drive spreadsheet connector functions are required; do not fall back to public exports because the roster is private. When the profile has `health_check_data_source_url`, use the Notion `query_data_sources` and `fetch` tools in read-only mode before preprocessing and pass only compact health-check candidates.

```javascript
const satisfaction = {
  spreadsheetId: SATISFACTION_SPREADSHEET_ID,
  dashboardRows: DASHBOARD_ROW_COUNT,
  learningRows: LEARNING_ROW_COUNT,
  operationRows: OPERATION_ROW_COUNT,
};
const roster = {
  spreadsheetId: ROSTER_SPREADSHEET_ID,
  rowCount: ROSTER_ROW_COUNT,
};
const sheets = {
  dashboard: SATISFACTION_DASHBOARD_SHEET,
  learning: SATISFACTION_LEARNING_SHEET,
  operation: SATISFACTION_OPERATION_SHEET,
  roster: ROSTER_SHEET,
};
const cohortQuery = String(PROFILE_COHORT_QUERY);
const rosterCohortLabel = ROSTER_COHORT_LABEL;
const rosterExcludedNames = ROSTER_EXCLUDED_NAMES; // optional array from profile, default []
const healthCheckDataSourceUrl = HEALTH_CHECK_DATA_SOURCE_URL; // optional; blank disables health-check integration
const preparer = ABSOLUTE_PREPARE_REPORT_DATA_PATH;
const windowResult = REPORT_WINDOW_RESULT;
const shellQuote = value => `'${value.replaceAll("'", "'\"'\"'")}'`;
const healthRiskLabels = new Set(["불만", "학습고민", "독려", "강성", "이슈상담", "진로상담", "하차예정", "하차", "관심이 필요함", "수강철회", "출결문의", "회피형", "소심함", "고민", "😣", "🤐"]);

const parseLabels = value => {
  if (Array.isArray(value)) return value.map(String).map(item => item.trim()).filter(Boolean);
  if (typeof value !== "string" || !value.trim()) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.map(String).map(item => item.trim()).filter(Boolean) : [];
  } catch {
    return value.split(",").map(item => item.trim()).filter(Boolean);
  }
};

const compactHealthText = pageText => {
  const content = pageText.match(/<content>([\s\S]*?)<\/content>/)?.[1] ?? pageText;
  return content
    .replaceAll(/<ancestor-path>[\s\S]*?<\/ancestor-path>/g, "")
    .replaceAll(/<properties>[\s\S]*?<\/properties>/g, "")
    .replaceAll(/<callout icon="❗">[\s\S]*?<\/callout>/g, "")
    .replaceAll(/<[^>]+>/g, " ")
    .replaceAll(/\s+/g, " ")
    .trim()
    .slice(0, 1600);
};

const sources = [
  { key: "learning_rows", spreadsheetId: satisfaction.spreadsheetId, sheetName: sheets.learning, searchColumn: "A", rowCount: satisfaction.learningRows, startColumn: "A", endColumn: "M", width: 13, query: cohortQuery, headerRow: 1 },
  { key: "operation_rows", spreadsheetId: satisfaction.spreadsheetId, sheetName: sheets.operation, searchColumn: "A", rowCount: satisfaction.operationRows, startColumn: "A", endColumn: "G", width: 7, query: cohortQuery, headerRow: 1 },
  { key: "learning_dashboard_rows", spreadsheetId: satisfaction.spreadsheetId, sheetName: sheets.dashboard, searchColumn: "A", rowCount: satisfaction.dashboardRows, startColumn: "A", endColumn: "J", width: 10, query: cohortQuery, headerRow: 1 },
  { key: "operation_dashboard_rows", spreadsheetId: satisfaction.spreadsheetId, sheetName: sheets.dashboard, searchColumn: "M", rowCount: satisfaction.dashboardRows, startColumn: "L", endColumn: "R", width: 7, query: cohortQuery, headerRow: 1 },
  { key: "roster_rows", spreadsheetId: roster.spreadsheetId, sheetName: sheets.roster, searchColumn: "A", rowCount: roster.rowCount, startColumn: "A", endColumn: "E", width: 5, query: rosterCohortLabel, headerRow: 2 },
];

const searchResults = await Promise.all(sources.map(source =>
  tools.mcp__codex_apps__google_drive_search_spreadsheet_rows({
    spreadsheet_id: source.spreadsheetId,
    sheet_name: source.sheetName,
    range: `${source.searchColumn}1:${source.searchColumn}${source.rowCount}`,
    query: source.query,
    header_row: source.headerRow,
    include_header_row: false,
    return_columns: [source.searchColumn],
    max_matching_rows: source.rowCount,
  })
));

const rowNumbers = result => {
  if (result.isError || !result.structuredContent?.markdown) throw new Error("cohort search failed");
  const data = result.structuredContent;
  if (data.truncated || data.truncated_rows || data.truncated_columns) throw new Error("cohort search truncated");
  return data.markdown.split("\n").slice(2).map(line => Number(line.split("|")[1]?.trim())).filter(Number.isInteger);
};

const cellValue = cell => {
  const effective = cell?.effectiveValue;
  if (effective && "numberValue" in effective) return effective.numberValue;
  if (effective && "stringValue" in effective) return effective.stringValue;
  if (effective && "boolValue" in effective) return effective.boolValue;
  return cell?.formattedValue ?? null;
};

const readRows = async (source, rows) => {
  const output = [];
  for (let offset = 0; offset < rows.length; offset += 50) {
    const batch = rows.slice(offset, offset + 50);
    const result = await tools.mcp__codex_apps__google_drive_get_spreadsheet_cells({
      spreadsheet_id: source.spreadsheetId,
      ranges: batch.map(row => `'${source.sheetName.replaceAll("'", "''")}'!${source.startColumn}${row}:${source.endColumn}${row}`),
      cell_fields: "formattedValue,effectiveValue",
    });
    if (result.isError || !Array.isArray(result.structuredContent?.sheets)) throw new Error("cohort row read failed");
    const blocks = result.structuredContent.sheets.flatMap(sheet => sheet.data).sort((left, right) => left.startRow - right.startRow);
    if (blocks.length !== batch.length) throw new Error("cohort row read was incomplete");
    for (const block of blocks) {
      const cells = block.rowData?.[0]?.values ?? [];
      output.push(Array.from({length: source.width}, (_, index) => cellValue(cells[index])));
    }
  }
  return output;
};

const rowSets = await Promise.all(sources.map((source, index) => readRows(source, rowNumbers(searchResults[index]))));
const data = Object.fromEntries(sources.map((source, index) => [source.key, rowSets[index]]));

const readHealthCheckNotes = async () => {
  if (!healthCheckDataSourceUrl) return [];
  const queryResult = await tools["mcp__codex_apps__notion._query_data_sources"]({
    data: {
      mode: "sql",
      data_source_urls: [healthCheckDataSourceUrl],
      query: `SELECT url, "수강생 이름", "기수", "date:상담일:start", "차수", "라벨" FROM "${healthCheckDataSourceUrl}" WHERE "기수" = ? AND ("date:상담일:start" IS NULL OR datetime("date:상담일:start") <= datetime(?)) ORDER BY COALESCE("date:상담일:start", createdTime) DESC LIMIT 100`,
      params: [rosterCohortLabel, windowResult.end],
    },
  });
  if (queryResult.isError) throw new Error("health-check query failed");
  const queryText = queryResult.structuredContent?.text ?? queryResult.content?.[0]?.text ?? queryResult.output ?? "";
  const rows = JSON.parse(queryText).results ?? [];
  const endDay = windowResult.end.slice(0, 10);
  const candidates = rows.filter(row => {
    const labels = parseLabels(row["라벨"]);
    const checkedAt = String(row["date:상담일:start"] ?? "").slice(0, 10);
    return labels.some(label => healthRiskLabels.has(label)) && (!checkedAt || checkedAt <= endDay);
  });
  const pages = await Promise.all(candidates.map(row => tools["mcp__codex_apps__notion._fetch"]({id: row.url})));
  return candidates.map((row, index) => {
    const pageText = pages[index].structuredContent?.text ?? pages[index].content?.[0]?.text ?? pages[index].output ?? "";
    return {
      name: String(row["수강생 이름"] ?? "").trim(),
      checked_at: String(row["date:상담일:start"] ?? "").slice(0, 10) || null,
      cycle: String(row["차수"] ?? "").trim() || null,
      labels: parseLabels(row["라벨"]),
      note: compactHealthText(pageText),
      url: row.url,
    };
  });
};

const healthCheckNotes = await readHealthCheckNotes();
const payload = JSON.stringify({
  cohort: cohortQuery,
  roster_cohort_label: rosterCohortLabel,
  comparison_start: windowResult.comparison_start,
  start: windowResult.start,
  end: windowResult.end,
  roster_excluded_names: rosterExcludedNames,
  health_check_notes: healthCheckNotes,
  ...data,
});
const prepared = await tools.exec_command({
  cmd: `printf '%s' ${shellQuote(payload)} | python3 -m uv run --quiet ${shellQuote(preparer)}`,
  yield_time_ms: 30000,
  max_output_tokens: 30000,
});
if (prepared.exit_code !== 0) throw new Error("report preprocessing failed");
const manifest = JSON.parse(prepared.output.trim());
let vocSequence = 0;
const vocItems = [];
const addVoc = item => {
  vocSequence += 1;
  item.id = `voc-${String(vocSequence).padStart(3, "0")}`;
  vocItems.push({
    id: item.id,
    name: item.name,
    score_label: item.score_label,
    original: item.original,
    long: manifest.validation.long_originals.includes(item.original),
  });
};
manifest.operation.general_voc.forEach(addVoc);
manifest.learning.forEach(survey => survey.voc.forEach(addVoc));
store("oz_weekly_manifest", manifest);
text(JSON.stringify({voc_items: vocItems, special_issues: manifest.special_issues}));
```

Do not call `text`, `notify`, or `yield_control` with search results, raw rows, the roster, or the complete manifest. The only allowed output is the compact decision view.
