import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const scriptsDirectory = path.dirname(fileURLToPath(import.meta.url));
const reference = readFileSync(
  path.join(scriptsDirectory, "..", "references", "source-read-orchestration.md"),
  "utf8",
);

assert.match(reference, /const cohortQuery = String\(PROFILE_COHORT_QUERY\);/);
assert.match(reference, /SATISFACTION_DASHBOARD_SHEET/);
assert.match(reference, /SATISFACTION_LEARNING_SHEET/);
assert.match(reference, /SATISFACTION_OPERATION_SHEET/);
assert.match(reference, /ROSTER_SHEET/);
assert.match(reference, /searchColumn: "M"/);
assert.match(reference, /headerRow: 2/);
assert.match(reference, /rosterExcludedNames/);
assert.match(reference, /python3 -m uv run --quiet/);
assert.match(reference, /healthCheckDataSourceUrl/);
assert.match(reference, /mcp__codex_apps__notion\._query_data_sources/);
assert.match(reference, /roster_excluded_names: rosterExcludedNames/);
assert.match(reference, /health_check_notes: healthCheckNotes/);
assert.doesNotMatch(reference, /public-sheet-source\.mjs|ABSOLUTE_PUBLIC_SHEET_SOURCE_PATH/);
assert.match(reference, /store\("oz_weekly_manifest", manifest\);/);
assert.doesNotMatch(reference, /text\(prepared\.output\);/);
