import { readFileSync } from "node:fs";

const MARKDOWN_CONTROLS = new Set([">", "<", "#", "-", "+", "*", "`", "|"]);

function invariant(condition, message) {
  if (!condition) throw new Error(message);
}

function markdownSafe(original) {
  let boundary = 0;
  while (boundary < original.length && MARKDOWN_CONTROLS.has(original[boundary])) boundary += 1;
  return [...original.slice(0, boundary)].map(character => `\\${character}`).join("") + original.slice(boundary);
}

function collectVoc(manifest) {
  const items = [];
  for (const item of manifest.operation.general_voc) items.push({ ...item, group: "operation" });
  for (const level of manifest.operation.level_classes) {
    for (const item of level.voc) items.push({ ...item, group: `level:${level.name}` });
  }
  for (const survey of manifest.learning) {
    for (const item of survey.voc) items.push({ ...item, group: `learning:${survey.subject}` });
  }
  return items;
}

function decisionIndex(payload, items) {
  invariant(Array.isArray(payload.voc_decisions), "voc_decisions must be an array");
  const expectedIds = new Set(items.map(item => item.id));
  invariant(expectedIds.size === items.length && !expectedIds.has(undefined), "manifest VOC IDs are invalid");
  const decisions = new Map();
  for (const decision of payload.voc_decisions) {
    invariant(typeof decision.id === "string" && !decisions.has(decision.id), "VOC decision IDs are duplicated");
    invariant(decision.category === "positive" || decision.category === "improvement", "VOC category is invalid");
    decisions.set(decision.id, decision);
  }
  const actualIds = new Set(decisions.keys());
  invariant(actualIds.size === expectedIds.size && [...expectedIds].every(id => actualIds.has(id)), "VOC decision IDs are incomplete");
  const longOriginals = new Set(payload.manifest.validation.long_originals);
  for (const item of items) {
    const summary = decisions.get(item.id).summary;
    if (longOriginals.has(item.original)) invariant(typeof summary === "string" && summary.trim(), `long VOC summary missing: ${item.id}`);
    else invariant(summary === undefined || summary === null || summary === "", `short VOC must not have a summary: ${item.id}`);
  }
  return decisions;
}

function issueIndex(payload) {
  invariant(Array.isArray(payload.issue_decisions), "issue_decisions must be an array");
  const expected = new Set(payload.manifest.special_issues.map(issue => issue.name));
  const decisions = new Map();
  for (const decision of payload.issue_decisions) {
    invariant(typeof decision.name === "string" && !decisions.has(decision.name), "issue decision names are duplicated");
    invariant(typeof decision.title === "string" && decision.title.trim() && !decision.title.includes("검토"), `issue title is invalid: ${decision.name}`);
    invariant(Array.isArray(decision.situation) && decision.situation.length > 0, `issue situation is missing: ${decision.name}`);
    invariant(decision.situation.every(item => typeof item === "string" && item.trim()), `issue situation is invalid: ${decision.name}`);
    invariant(decision.responses === undefined || Array.isArray(decision.responses), `issue responses are invalid: ${decision.name}`);
    decisions.set(decision.name, decision);
  }
  invariant([...expected].every(name => decisions.has(name)), "issue decision names are incomplete");
  return decisions;
}

function renderItems(items, decisions, longOriginals, indentation) {
  const lines = [];
  for (const item of items) {
    const decision = decisions.get(item.id);
    const original = markdownSafe(item.original);
    const isLong = longOriginals.has(item.original);
    if (!isLong) {
      const label = decision.category === "improvement" ? ` (${item.name}님 - ${item.score_label})` : "";
      lines.push(`${indentation}- ${original}${label}`);
      continue;
    }
    const label = decision.category === "improvement" ? `${item.name}님 - ${item.score_label}` : `${item.name}님`;
    lines.push(`${indentation}- ${decision.summary.trim()} (${label})`);
    lines.push(`${indentation}  - 원문 보기`);
    lines.push(`${indentation}    - ${original}`);
  }
  return lines;
}

function renderGroup(items, decisions, longOriginals, headingIndent = "") {
  const itemIndent = `${headingIndent}  `;
  const positive = items.filter(item => decisions.get(item.id).category === "positive");
  const improvement = items.filter(item => decisions.get(item.id).category === "improvement");
  return [
    `${headingIndent}- **긍정 피드백**`,
    ...(positive.length ? renderItems(positive, decisions, longOriginals, itemIndent) : [`${itemIndent}- 추가 긍정 의견 없음`]),
    `${headingIndent}- **개선 및 제안 사항**`,
    ...(improvement.length ? renderItems(improvement, decisions, longOriginals, itemIndent) : [`${itemIndent}- 추가 개선 의견 없음`]),
  ];
}

function metricRows(survey, columns) {
  const empty = { content: "", live: "", assignment: "", achievement: "" };
  const metrics = survey?.metrics ?? empty;
  const subject = survey?.subject ?? "";
  return columns === 2
    ? [
        `| **콘텐츠 만족도** | ${metrics.content} |`, `| **실시간 만족도** | ${metrics.live} |`,
        `| **과제 만족도** | ${metrics.assignment} |`, `| **교과목 만족도** | ${metrics.achievement} |`,
      ]
    : [
        `| **콘텐츠 만족도** | ${metrics.content} | ${subject} |`, `| **실시간 만족도** | ${metrics.live} |  |`,
        `| **과제 만족도** | ${metrics.assignment} |  |`, `| **교과목 만족도** | ${metrics.achievement} |  |`,
      ];
}

function quantitativeSection(manifest) {
  const previousSurvey = manifest.previous_learning[0];
  const currentSurveys = manifest.learning.length ? manifest.learning : [undefined];
  const lines = [
    "## 정량 보고", "", "**지난주**", "",
    `| **운영 만족도** | ${manifest.operation.previous.score ?? ""} (${manifest.operation.previous.respondent_count}/${manifest.operation.previous.current_count ?? ""}) |`,
    "| --- | --- |", ...metricRows(previousSurvey, 2), "", "**이번주**", "",
    `| **운영 만족도** | ${manifest.operation.current.score ?? ""} (${manifest.operation.current.respondent_count}/${manifest.operation.current.current_count ?? ""}) |  |`,
    "| --- | --- | --- |",
  ];
  currentSurveys.forEach((survey, index) => {
    if (index > 0) lines.push("", `| **추가 조사 과목** |  | ${survey.subject} |`);
    lines.push(...metricRows(survey, 3));
  });
  return lines;
}

function missingResponseSection(manifest) {
  if (!manifest.missing_responses.length && !manifest.source_warnings.length) return [];
  const lines = ["", "## 미응답 수강생"];
  for (const group of manifest.missing_responses) {
    const label = group.subject ? `${group.survey} - ${group.subject}` : group.survey;
    const names = group.names.length ? group.names.join(", ") : "없음";
    lines.push(`- **${label} (${group.names.length}명)**: ${names}`);
  }
  if (manifest.source_warnings.length) {
    lines.push("", "- **데이터 확인 필요**");
    for (const warning of manifest.source_warnings) lines.push(`  - ${warning}`);
  }
  return lines;
}

function issueSection(manifest, decisions) {
  if (!decisions.size) return [];
  const lines = ["", "## 특이사항"];
  for (const decision of decisions.values()) {
    const responses = decision.responses?.length ? decision.responses : ["확인된 운영진 대응 내용 없음(수기 보완 필요)"];
    lines.push("", `- **${decision.name} — ${decision.title.trim()}**`, "", "  `상황`", "");
    for (const fact of decision.situation) lines.push(`  - ${fact.trim()}`);
    lines.push("", "  `운영진 대응 및 결과`", "");
    for (const response of responses) lines.push(`  - ${response.trim()}`);
  }
  return lines;
}

function operationSections(manifest, items, decisions, longOriginals) {
  if (!manifest.validation.operation_voc_required) return [];
  const date = manifest.operation.current.survey_date.slice(5).replace("-", "/");
  const general = items.filter(item => item.group === "operation");
  const lines = ["", `## 📊 ${date} 운만조 VOC 요약`, "", ...renderGroup(general, decisions, longOriginals)];
  if (manifest.operation.level_classes.length) lines.push("", "#### 수준별 학습반");
  for (const level of manifest.operation.level_classes) {
    const levelItems = items.filter(item => item.group === `level:${level.name}`);
    lines.push("", `- **${level.name}**`, ...renderGroup(levelItems, decisions, longOriginals, "  "));
  }
  return lines;
}

function learningSections(manifest, items, decisions, longOriginals) {
  const lines = [];
  for (const survey of manifest.learning) {
    const date = survey.survey_date.slice(5).replace("-", "/");
    const surveyItems = items.filter(item => item.group === `learning:${survey.subject}`);
    lines.push("", `## 📊 ${date} 학만조 VOC _${survey.subject}`, "", ...renderGroup(surveyItems, decisions, longOriginals));
  }
  return lines;
}

function dashboardSection(manifest) {
  if (!manifest.validation.dashboard_required) return [];
  const lines = ["", "## 운영 대시보드 입력용"];
  for (const survey of manifest.learning) {
    const currentCount = survey.metrics.current_count == null ? "" : `${survey.metrics.current_count}명`;
    if (manifest.learning.length > 1) lines.push("", `**${survey.subject}**`);
    lines.push("", "| 대시보드 구분 | 만족도 | 응답 인원 | 현재 인원 | 실시일 |", "| --- | --- | --- | --- | --- |",
      `| 라이브 세션 만족도 | ${survey.metrics.live} | ${survey.metrics.respondent_count}명 | ${currentCount} | ${survey.survey_date} |`,
      `| 과제 만족도 | ${survey.metrics.assignment} | ${survey.metrics.respondent_count}명 | ${currentCount} | ${survey.survey_date} |`,
      `| 성취도 | ${survey.metrics.achievement} | ${survey.metrics.respondent_count}명 | ${currentCount} | ${survey.survey_date} |`,
      `| VOD 만족도 | ${survey.metrics.content} | ${survey.metrics.respondent_count}명 | ${currentCount} | ${survey.survey_date} |`);
  }
  return lines;
}

function renderReport(payload) {
  invariant(payload && typeof payload === "object", "input must be an object");
  invariant(/^\d{5}$/.test(payload.writing_id), "writing_id must contain five digits");
  const items = collectVoc(payload.manifest);
  const decisions = decisionIndex(payload, items);
  const issues = issueIndex(payload);
  const longOriginals = new Set(payload.manifest.validation.long_originals);
  return [
    `:::writing{variant="document" id="${payload.writing_id}"}`,
    ...quantitativeSection(payload.manifest),
    ...missingResponseSection(payload.manifest),
    ...issueSection(payload.manifest, issues),
    ...operationSections(payload.manifest, items, decisions, longOriginals),
    ...learningSections(payload.manifest, items, decisions, longOriginals),
    ...dashboardSection(payload.manifest),
    ":::"
  ].join("\n");
}

try {
  process.stdout.write(`${renderReport(JSON.parse(readFileSync(0, "utf8")))}\n`);
} catch (error) {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
}
