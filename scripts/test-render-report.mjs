import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const scriptsDirectory = path.dirname(fileURLToPath(import.meta.url));
const renderer = path.join(scriptsDirectory, "render-report.mjs");
const validator = path.join(scriptsDirectory, "validate-report.py");

const manifest = {
  operation: {
    previous: { score: "4.7", respondent_count: 35, survey_date: "2026-07-31", current_count: 40, dashboard_response_count: 35 },
    current: { score: "4.9", respondent_count: 36, survey_date: "2026-08-07", current_count: 40, dashboard_response_count: 36 },
    general_voc: [
      { id: "operation-general-1", name: "김하나", original: "짧은 긍정 원문", score_label: "5점" },
    ],
    level_classes: [],
  },
  previous_learning: [],
  learning: [
    {
      subject: "UI 디자인 실무",
      survey_date: "2026-08-07",
      metrics: { content: "4.7", live: "4.7", assignment: "4.5", achievement: "4.6", respondent_count: 36, current_count: 40, dashboard_response_count: 36 },
      voc: [
        { id: "learning-1", name: "박셋", original: "긴 학습 원문\n둘째 줄\n셋째 줄\n넷째 줄", score_label: "콘텐츠 5점·실시간 4점·과제 4점" },
      ],
    },
  ],
  special_issues: [
    { name: "이둘", operation_score: 3, learning_scores: [] },
  ],
  missing_responses: [
    { survey: "운영 만족도", subject: null, names: ["미응답자"] },
  ],
  source_warnings: ["운영 만족도 현재 인원 불일치: 대시보드 40명 / 마스터시트 훈련중 41명"],
  validation: {
    required_originals: ["짧은 긍정 원문", "긴 학습 원문\n둘째 줄\n셋째 줄\n넷째 줄"],
    long_originals: ["긴 학습 원문\n둘째 줄\n셋째 줄\n넷째 줄"],
    special_issue_names: ["이둘"],
    operation_voc_required: true,
    level_classes: [],
    learning_subjects: ["UI 디자인 실무"],
    dashboard_required: true,
    missing_response_names: ["미응답자"],
    missing_response_required: true,
    source_warning_required: true,
  },
};

const payload = {
  manifest,
  writing_id: "12345",
  voc_decisions: [
    { id: "operation-general-1", category: "positive" },
    { id: "learning-1", category: "positive", summary: "실습 흐름을 이해하는 데 도움이 됨" },
  ],
  issue_decisions: [
    { name: "이둘", title: "운영 만족도 상담 필요 (3점)", situation: ["운영 만족도 3점이 확인됨."], responses: [] },
    { name: "수기인물", title: "출결 이슈", situation: ["수기 출결 이슈가 전달됨."], responses: ["개별 확인 예정."] },
  ],
};

const completed = spawnSync(process.execPath, [renderer], {
  input: JSON.stringify(payload),
  encoding: "utf8",
});

assert.equal(completed.status, 0, completed.stderr);
for (const original of manifest.validation.required_originals) {
  assert.equal(completed.stdout.split(original).length - 1, 1, original);
}
assert.match(completed.stdout, /운영 만족도 \(1명\).*미응답자/);
assert.match(completed.stdout, /실습 흐름을 이해하는 데 도움이 됨 \(박셋님\)/);
assert.match(completed.stdout, /확인된 운영진 대응 내용 없음\(수기 보완 필요\)/);
assert.match(completed.stdout, /수기인물 — 출결 이슈/);
assert.doesNotMatch(completed.stdout, /짧은 긍정 원문[\s\S]{0,80}원문 보기/);

const specialIssueNames = payload.issue_decisions.map(item => item.name);
const validated = spawnSync("python3", ["-m", "uv", "run", "--quiet", validator], {
  input: JSON.stringify({ report: completed.stdout.trimEnd(), ...manifest.validation, special_issue_names: specialIssueNames }),
  encoding: "utf8",
});
assert.equal(validated.status, 0, validated.stderr);
assert.equal(validated.stdout.trim(), '{"valid":true}');

const incomplete = spawnSync(process.execPath, [renderer], {
  input: JSON.stringify({ ...payload, voc_decisions: payload.voc_decisions.slice(1) }),
  encoding: "utf8",
});
assert.notEqual(incomplete.status, 0);
assert.match(incomplete.stderr, /VOC decision IDs/);
