import assert from "node:assert/strict";
import { buildPublicSheetQueryUrl, fetchPublicSheetRows, parseCsv } from "./public-sheet-source.mjs";

const operationCsv = [
  "기수,이름,운영 만족도,운영 이유,수준별 학습,반,도움 여부,수준별 이유,기타 의견,제출 시각,응답 토큰",
  "13기,synthetic-respondent-a,5,\"쉼표가 있는 의견, 계속합니다\",예,새싹반,도움이 되었다,복습에 도움이 됨,,2026-08-07 07:06:00,synthetic-token-a",
  "12기,synthetic-respondent-b,1,다른 기수,, ,,,,2026-08-07 07:07:00,synthetic-token-b",
].join("\n");

const learningCsv = [
  "기수,이름,교과목,콘텐츠 만족도,실시간 세션 만족도,과제 난이도,과제 만족도,이해도,VOC,미사용1,미사용2,제출 시각,응답 토큰",
  "13,synthetic-respondent-a,UI 디자인 실무,4.5,4.7,적당,4.0,높음,\"첫 줄\n둘째 줄\",,,2026-08-07 07:06:00,synthetic-token-c",
].join("\n");

const operationUrl = "https://docs.google.com/spreadsheets/d/operation-id/edit?gid=12345#gid=12345";
const learningUrl = "https://docs.google.com/spreadsheets/d/learning-id/edit?gid=67890#gid=67890";

const operationQuery = buildPublicSheetQueryUrl(operationUrl, {
  endColumn: "K",
  cohortValue: "13기",
  timestampColumn: "J",
});
assert.equal(new URL(operationQuery).searchParams.get("gid"), "12345");
assert.match(new URL(operationQuery).searchParams.get("tq") ?? "", /select A,B,C,D,E,F,G,H,I,J,K/);
assert.match(new URL(operationQuery).searchParams.get("tq") ?? "", /where A = '13기'/);
assert.match(new URL(operationQuery).searchParams.get("tq") ?? "", /J is not null/);

const parsed = parseCsv(operationCsv);
assert.equal(parsed.length, 3);
assert.equal(parsed[1][3], "쉼표가 있는 의견, 계속합니다");

const requestedUrls = [];
const rows = await fetchPublicSheetRows({
  sourceUrl: operationUrl,
  cohortNumber: "13",
  endColumn: "K",
  width: 11,
  requestText: async url => {
    requestedUrls.push(url);
    return operationCsv;
  },
});
assert.equal(rows.length, 1);
assert.equal(rows[0][0], "13기");
assert.equal(rows[0][3], "쉼표가 있는 의견, 계속합니다");
assert.ok(requestedUrls.length >= 1);

const headerlessRows = await fetchPublicSheetRows({
  sourceUrl: operationUrl,
  cohortNumber: "13",
  endColumn: "K",
  width: 11,
  requestText: async () => operationCsv.split("\n").slice(1).join("\n"),
});
assert.equal(headerlessRows.length, 1);
assert.equal(headerlessRows[0][1], "synthetic-respondent-a");

const learningRows = await fetchPublicSheetRows({
  sourceUrl: learningUrl,
  cohortNumber: "13기",
  endColumn: "M",
  width: 13,
  requestText: async () => learningCsv,
});
assert.equal(learningRows.length, 1);
assert.equal(learningRows[0][0], "13");
assert.equal(learningRows[0][8], "첫 줄\n둘째 줄");

await assert.rejects(
  fetchPublicSheetRows({
    sourceUrl: operationUrl,
    cohortNumber: "13",
    endColumn: "K",
    width: 11,
    requestText: async () => "<html>Google login</html>",
  }),
  error => error instanceof Error && error.code === "INVALID_CSV",
);

await assert.rejects(
  fetchPublicSheetRows({
    sourceUrl: operationUrl,
    cohortNumber: "12",
    endColumn: "K",
    width: 11,
    requestText: async () => "",
  }),
  error => error instanceof Error && error.code === "NO_COHORT_ROWS",
);
