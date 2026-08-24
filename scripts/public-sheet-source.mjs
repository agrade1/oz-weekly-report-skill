import { readFileSync } from "node:fs";
import { execFile } from "node:child_process";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const MAX_RESPONSE_BYTES = 12_000_000;
const REQUEST_TIMEOUT_MS = 20_000;
const execFileAsync = promisify(execFile);
const COLUMNS_BY_END = Object.freeze({ K: "A,B,C,D,E,F,G,H,I,J,K", M: "A,B,C,D,E,F,G,H,I,J,K,L,M" });

export class PublicSheetError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "PublicSheetError";
    this.code = code;
  }
}

function normalizeCohortNumber(value) {
  const normalized = String(value ?? "").trim().replace(/\s+/g, "").replace(/기$/u, "");
  if (!/^\d+$/.test(normalized)) throw new PublicSheetError("INVALID_COHORT", "cohort must be a number or number기");
  return normalized;
}

function normalizeCell(value) {
  return String(value ?? "").replace(/^\uFEFF/u, "").trim();
}

function cohortCellMatches(value, cohortNumber) {
  return normalizeCell(value).replace(/기$/u, "") === cohortNumber;
}

function sheetIdentity(sourceUrl) {
  let parsed;
  try {
    parsed = new URL(sourceUrl);
  } catch (error) {
    throw new PublicSheetError("INVALID_SOURCE_URL", "configured source URL is invalid");
  }
  if (parsed.protocol !== "https:" || parsed.hostname !== "docs.google.com") {
    throw new PublicSheetError("UNSUPPORTED_SOURCE_URL", "public fallback requires a Google Sheets URL");
  }
  const idMatch = parsed.pathname.match(/\/spreadsheets\/d\/([^/]+)/u);
  const hashGid = parsed.hash.match(/gid=(\d+)/u)?.[1];
  const gid = parsed.searchParams.get("gid") ?? hashGid;
  if (!idMatch?.[1] || !gid) throw new PublicSheetError("INVALID_SOURCE_URL", "Google Sheets URL must include spreadsheet id and gid");
  return { id: idMatch[1], gid };
}

export function buildPublicSheetQueryUrl(sourceUrl, options) {
  const { id, gid } = sheetIdentity(sourceUrl);
  const columns = COLUMNS_BY_END[options.endColumn];
  if (!columns) throw new PublicSheetError("UNSUPPORTED_SCHEMA", `unsupported source end column: ${options.endColumn}`);
  const cohortValue = String(options.cohortValue ?? "").trim();
  if (!cohortValue) throw new PublicSheetError("INVALID_COHORT", "cohort query value is empty");
  const escaped = cohortValue.replaceAll("'", "''");
  const predicate = options.numeric ? escaped : `'${escaped}'`;
  const timestampColumn = options.timestampColumn;
  if (timestampColumn !== undefined && !["J", "L"].includes(timestampColumn)) {
    throw new PublicSheetError("UNSUPPORTED_SCHEMA", `unsupported timestamp column: ${timestampColumn}`);
  }
  const endpoint = new URL(`https://docs.google.com/spreadsheets/d/${id}/gviz/tq`);
  endpoint.searchParams.set("gid", gid);
  endpoint.searchParams.set("tqx", "out:csv");
  endpoint.searchParams.set("tq", `select ${columns} where A = ${predicate}${timestampColumn ? ` and ${timestampColumn} is not null` : ""}`);
  return endpoint.toString();
}

export function parseCsv(source) {
  if (typeof source !== "string") throw new PublicSheetError("INVALID_CSV", "public source did not return text");
  if (/^\s*<(?:!doctype\s+html|html\b)/iu.test(source)) throw new PublicSheetError("INVALID_CSV", "public source returned HTML instead of CSV");
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < source.length; index += 1) {
    const character = source[index];
    const next = source[index + 1];
    if (quoted) {
      if (character === '"' && next === '"') {
        cell += '"';
        index += 1;
      } else if (character === '"') {
        quoted = false;
      } else {
        cell += character;
      }
    } else if (character === '"' && cell.length === 0) {
      quoted = true;
    } else if (character === ",") {
      row.push(cell);
      cell = "";
    } else if (character === "\n") {
      row.push(cell);
      if (row.some(value => value.length > 0)) rows.push(row);
      row = [];
      cell = "";
    } else if (character === "\r" && next === "\n") {
      continue;
    } else {
      cell += character;
    }
  }
  if (quoted) throw new PublicSheetError("INVALID_CSV", "public CSV contains an unterminated quoted cell");
  if (cell.length > 0 || row.length > 0) {
    row.push(cell);
    if (row.some(value => value.length > 0)) rows.push(row);
  }
  return rows;
}

function rowsFromCsv(source, width) {
  const rows = parseCsv(source);
  if (rows.length < 1) throw new PublicSheetError("NO_COHORT_ROWS", "public source returned no CSV rows");
  if (rows.some(row => row.length !== width)) {
    throw new PublicSheetError("SCHEMA_MISMATCH", "public source row width does not match the approved range");
  }
  const firstCell = normalizeCell(rows[0][0]).toLowerCase();
  const hasHeader = firstCell === "기수" || firstCell === "cohort";
  const dataRows = hasHeader ? rows.slice(1) : rows;
  return dataRows;
}

async function requestText(url) {
  let parsed;
  try {
    parsed = new URL(url);
  } catch (error) {
    throw new PublicSheetError("INVALID_SOURCE_URL", "public request URL is invalid");
  }
  if (parsed.protocol !== "https:") throw new PublicSheetError("UNSAFE_REDIRECT", "public source must remain HTTPS");
  const statusMarker = "\n__OZ_STATUS__";
  let result;
  try {
    result = await execFileAsync("curl", [
      "-sS", "-L", "--proto", "=https", "--proto-redir", "=https",
      "--max-time", String(REQUEST_TIMEOUT_MS / 1000),
      "--max-filesize", String(MAX_RESPONSE_BYTES),
      "-H", "accept: text/csv,text/plain;q=0.9",
      "-w", `${statusMarker}%{http_code}`,
      parsed.toString(),
    ], { maxBuffer: MAX_RESPONSE_BYTES + 1024 });
  } catch (error) {
    throw new PublicSheetError("PUBLIC_SOURCE_UNAVAILABLE", "public source request failed");
  }
  const output = result.stdout;
  const markerIndex = output.lastIndexOf(statusMarker);
  if (markerIndex < 0) throw new PublicSheetError("PUBLIC_SOURCE_UNAVAILABLE", "public source response was incomplete");
  const status = Number(output.slice(markerIndex + statusMarker.length));
  if (!Number.isInteger(status) || status < 200 || status >= 300) {
    throw new PublicSheetError("PUBLIC_SOURCE_UNAVAILABLE", `public source returned HTTP ${status || 0}`);
  }
  return output.slice(0, markerIndex);
}

export async function fetchPublicSheetRows(options) {
  const cohortNumber = normalizeCohortNumber(options.cohortNumber);
  const width = Number(options.width);
  if (!Number.isInteger(width) || ![11, 13].includes(width)) throw new PublicSheetError("UNSUPPORTED_SCHEMA", "approved source width must be 11 or 13");
  const reader = options.requestText ?? requestText;
  const variants = [
    { cohortValue: `${cohortNumber}기`, numeric: false },
    { cohortValue: cohortNumber, numeric: false },
    { cohortValue: cohortNumber, numeric: true },
  ];
  const uniqueRows = new Map();
  let successfulQuery = false;
  let lastError;
  for (const variant of variants) {
    const url = buildPublicSheetQueryUrl(options.sourceUrl, {
      endColumn: options.endColumn,
      timestampColumn: options.timestampColumn,
      ...variant,
    });
    try {
      const source = await reader(url);
      const rows = rowsFromCsv(source, width);
      successfulQuery = true;
      for (const row of rows) {
        if (cohortCellMatches(row[0], cohortNumber)) uniqueRows.set(JSON.stringify(row), row);
      }
    } catch (error) {
      lastError = error;
    }
  }
  if (uniqueRows.size === 0) {
    if (!successfulQuery && lastError instanceof PublicSheetError) throw lastError;
    throw new PublicSheetError("NO_COHORT_ROWS", `public source returned no rows for cohort ${cohortNumber}`);
  }
  return [...uniqueRows.values()];
}

async function main() {
  const input = JSON.parse(readFileSync(0, "utf8"));
  const rows = await fetchPublicSheetRows({
    sourceUrl: input.source_url,
    cohortNumber: input.cohort,
    endColumn: input.end_column,
    width: input.width,
    timestampColumn: input.timestamp_column,
  });
  process.stdout.write(`${JSON.stringify(rows)}\n`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch(error => {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  });
}
