#!/usr/bin/env node
/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * Static claim audit for the local IMAGINA instrument.
 *
 * It does two things:
 * 1. scans JSX/TS text for prohibited affirmative claims, allowing explicit
 *    boundary statements and rejected-claim examples;
 * 2. verifies that every evidenceId used by the UI exists in the evidence
 *    registry.
 *
 * This is a guardrail, not a semantic proof. The generated artifact is shown
 * on /method so the boundary can be inspected locally.
 */

const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

const ROOT = path.resolve(__dirname, "..");
const CLAIMS_PATH = path.join(ROOT, "lib", "claims.json");
const REGISTRY_PATH = path.join(ROOT, "lib", "evidence", "registry.json");
const AUDIT_PATH = path.join(ROOT, "lib", "evidence", "audit.json");
const SCAN_DIRS = [path.join(ROOT, "app"), path.join(ROOT, "components")];

const NEGATION = /\b(not|no|none|never|neither|nor|cannot|can't|without|does not|do not|is not|isn't|aren't|prohibited|forbidden|rejected|unauthori[sz]ed|not established|not a research goal|not allowed|never claim)\b|[✗×]/i;

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (error) {
    console.error(`[claim-audit] cannot read ${path.relative(ROOT, file)}: ${error.message}`);
    process.exit(1);
  }
}

function collectFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "node_modules" || entry.name === ".next" || entry.name === "__tests__") continue;
      files.push(...collectFiles(full));
    } else if (/\.(ts|tsx)$/.test(entry.name) && !entry.name.endsWith(".test.ts") && !entry.name.endsWith(".test.tsx")) {
      files.push(full);
    }
  }
  return files;
}

function lineContext(source, line) {
  const lines = source.split(/\r?\n/);
  return lines.slice(Math.max(0, line - 12), Math.min(lines.length, line + 12)).join(" ");
}

function visitTextNodes(file, source, onText) {
  const kind = file.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const sourceFile = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, kind);
  const walk = (node) => {
    if (ts.isJsxText(node) || ts.isStringLiteralLike(node)) {
      const text = node.getText(sourceFile).replace(/^["'`]|["'`]$/g, "");
      if (text.trim().length >= 4) {
        const { line } = sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile));
        onText(text, line + 1, node);
      }
    }
    ts.forEachChild(node, walk);
  };
  walk(sourceFile);
}

function main() {
  const claims = readJson(CLAIMS_PATH);
  const registry = readJson(REGISTRY_PATH);
  const ids = new Set(registry.entries.map((entry) => entry.id));
  const files = SCAN_DIRS.flatMap(collectFiles);
  const findings = [];
  const usedIds = new Set();
  const seen = new Set();

  for (const file of files) {
    const relative = path.relative(ROOT, file).replaceAll("\\", "/");
    const source = fs.readFileSync(file, "utf8");
    visitTextNodes(file, source, (text, line) => {
      const normalized = text.replace(/\s+/g, " ").trim();
      const lower = normalized.toLowerCase();
      const context = lineContext(source, line);
      for (const phrase of claims.prohibitedClaims) {
        let index = lower.indexOf(phrase.toLowerCase());
        while (index >= 0) {
          const key = `${relative}:${line}:${phrase}`;
          if (!seen.has(key)) {
            seen.add(key);
            const local = normalized.slice(Math.max(0, index - 100), index + phrase.length + 100);
            findings.push({
              file: relative,
              line,
              phrase,
              text: normalized.slice(0, 180),
              negated: NEGATION.test(`${local} ${context}`),
            });
          }
          index = lower.indexOf(phrase.toLowerCase(), index + phrase.length);
        }
      }
    });

    const kind = file.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
    const sourceFile = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, kind);
    const walk = (node) => {
      const named = ts.isJsxAttribute(node)
        ? node.name.getText(sourceFile) === "evidenceId"
        : ts.isPropertyAssignment(node)
          ? node.name.getText(sourceFile) === "evidenceId"
          : false;
      if (named && node.initializer && ts.isStringLiteralLike(node.initializer)) {
        usedIds.add(node.initializer.text);
      }
      ts.forEachChild(node, walk);
    };
    walk(sourceFile);
  }

  const orphanIds = [...usedIds].filter((id) => !ids.has(id));
  const affirmative = findings.filter((finding) => !finding.negated);
  const status = affirmative.length === 0 && orphanIds.length === 0 ? "pass" : "fail";
  const audit = {
    schema: "IMAGINA-EVIDENCE-AUDIT-v1",
    generatedAt: new Date().toISOString(),
    filesScanned: files.length,
    entries: registry.entries.length,
    evidenceIds: [...usedIds].sort(),
    evidenceIdCount: usedIds.size,
    orphanIds,
    findings,
    status,
  };

  if (process.argv.includes("--write")) {
    fs.writeFileSync(AUDIT_PATH, `${JSON.stringify(audit, null, 2)}\n`, "utf8");
    console.log(`[claim-audit] wrote ${path.relative(ROOT, AUDIT_PATH)}`);
  }

  console.log(
    `[claim-audit] ${status.toUpperCase()} · ${files.length} files · ${findings.length} phrase matches ` +
      `(${affirmative.length} affirmative) · ${usedIds.size} evidence ids · ${orphanIds.length} orphan`,
  );
  for (const finding of affirmative.slice(0, 20)) {
    console.error(`  ${finding.file}:${finding.line}  “${finding.phrase}”  in “${finding.text}”`);
  }
  for (const id of orphanIds.slice(0, 20)) {
    console.error(`  unknown evidenceId: ${id}`);
  }

  if (status !== "pass" && !process.argv.includes("--write")) process.exit(1);
  if (status !== "pass" && process.argv.includes("--write")) process.exit(1);
}

main();
