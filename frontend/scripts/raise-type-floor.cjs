#!/usr/bin/env node
/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * Raises arbitrary Tailwind text sizes below the platform floor (11px).
 *
 * Usage:
 *   node scripts/raise-type-floor.cjs        # report only
 *   node scripts/raise-type-floor.cjs --write
 */
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");
const TARGETS = ["app", "components"];
const PATTERN = /text-\[(?:[0-9]|10)px\]/g;
const write = process.argv.includes("--write");
let files = 0;
let hits = 0;

function walk(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      walk(absolute);
      continue;
    }
    if (!entry.name.endsWith(".tsx")) continue;
    const source = fs.readFileSync(absolute, "utf8");
    const matches = source.match(PATTERN);
    if (!matches) continue;
    files += 1;
    hits += matches.length;
    if (write) {
      fs.writeFileSync(absolute, source.replace(PATTERN, "text-[11px]"), "utf8");
    }
    console.log(`${write ? "rewrote" : "found"} ${matches.length.toString().padStart(3)}  ${path.relative(ROOT, absolute)}`);
  }
}

for (const target of TARGETS) walk(path.join(ROOT, target));
console.log(`\n${hits} size${hits === 1 ? "" : "s"} below 11px in ${files} file${files === 1 ? "" : "s"}.`);
if (!write) console.log("Run with --write to raise every occurrence to 11px.");
