#!/usr/bin/env node
/* eslint-disable @typescript-eslint/no-require-imports */
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const zlib = require("node:zlib");

const ROOT = path.resolve(__dirname, "..");
const NEXT_DIR = path.join(ROOT, ".next");
const BUILD_MANIFEST = path.join(NEXT_DIR, "build-manifest.json");
const APP_BUILD_MANIFEST = path.join(NEXT_DIR, "app-build-manifest.json");
const SERVER_APP = path.join(NEXT_DIR, "server", "app");

const KB = 1024;
const BUDGETS = {
  // Measured Next 16 + React 19 baseline; treated as a regression ceiling, not an aspiration.
  shared: 220 * KB,
  non3d: 340 * KB,
  threeD: 540 * KB,
};

const THREE_D = /^\/animus\/(observatory|practice|interview)\//;
const gzipCache = new Map();

function gzipSize(file) {
  const normalized = file.replace(/^\//, "").replace(/^_next\//, "");
  if (gzipCache.has(normalized)) return gzipCache.get(normalized);
  const absolute = path.join(NEXT_DIR, normalized);
  if (!fs.existsSync(absolute)) {
    gzipCache.set(normalized, 0);
    return 0;
  }
  const size = zlib.gzipSync(fs.readFileSync(absolute), { level: 9 }).length;
  gzipCache.set(normalized, size);
  return size;
}

function sizeOf(files) {
  return [...new Set(files)].reduce((total, file) => total + gzipSize(file), 0);
}

function chunkFiles(text) {
  return [...text.matchAll(/static\/chunks\/[^"']+\.js/g)].map((match) => match[0]);
}

function sharedFromBuildManifest() {
  if (!fs.existsSync(BUILD_MANIFEST)) return [];
  const manifest = JSON.parse(fs.readFileSync(BUILD_MANIFEST, "utf8"));
  return [...(manifest.polyfillFiles || []), ...(manifest.rootMainFiles || [])];
}

function walkManifests(directory) {
  if (!fs.existsSync(directory)) return [];
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) return walkManifests(absolute);
    return entry.isFile() && entry.name === "page_client-reference-manifest.js" ? [absolute] : [];
  });
}

function routeFromManifest(file) {
  const relative = path.relative(SERVER_APP, path.dirname(file)).replaceAll("\\", "/");
  const route = relative === "" || relative === "." ? "/" : `/${relative}`;
  return route.endsWith("/page") ? route.slice(0, -5) || "/" : route;
}

function turbopackRoutes() {
  const shared = sharedFromBuildManifest();
  const layoutChunks = new Set();
  const routes = [];

  for (const file of walkManifests(SERVER_APP)) {
    const text = fs.readFileSync(file, "utf8");
    const entrySection = text.match(/"entryJSFiles":\{(.*?)\}\};/s);
    if (!entrySection) continue;

    const layout = entrySection[1].match(/\[project\]\/app\/layout":\[(.*?)\]/s);
    if (layout) for (const chunk of chunkFiles(layout[1])) layoutChunks.add(chunk);

    routes.push({
      route: routeFromManifest(file),
      files: [...shared, ...chunkFiles(entrySection[1])],
    });
  }

  const sharedFiles = [...shared, ...layoutChunks];
  return {
    routes: routes.map((entry) => ({
      route: entry.route,
      bytes: sizeOf([...sharedFiles, ...entry.files]),
      threeD: THREE_D.test(entry.route),
    })),
    sharedBytes: sizeOf(sharedFiles),
  };
}

function webpackRoutes() {
  if (!fs.existsSync(APP_BUILD_MANIFEST)) return null;
  const manifest = JSON.parse(fs.readFileSync(APP_BUILD_MANIFEST, "utf8"));
  const pages = manifest.pages || {};
  const shared = sharedFromBuildManifest();
  const counts = new Map();
  for (const files of Object.values(pages)) {
    for (const file of new Set(files || [])) counts.set(file, (counts.get(file) || 0) + 1);
  }
  const sharedFiles = [...shared, ...[...counts.entries()].filter(([, count]) => count === Object.keys(pages).length).map(([file]) => file)];
  return {
    routes: Object.entries(pages).map(([route, files]) => ({
      route,
      bytes: sizeOf([...sharedFiles, ...(files || [])]),
      threeD: THREE_D.test(route),
    })),
    sharedBytes: sizeOf(sharedFiles),
  };
}

const turbopack = turbopackRoutes();
const result = turbopack.routes.length > 0 ? turbopack : webpackRoutes();

if (!result || result.routes.length === 0) {
  console.error("[bundle-budget] No app routes found. Run `next build` first.");
  process.exit(2);
}

const routes = result.routes.sort((a, b) => b.bytes - a.bytes);
let failures = 0;
console.log(
  `[bundle-budget] ${routes.length} routes · shared ${(result.sharedBytes / KB).toFixed(1)} KB gzip`,
);

for (const route of routes.slice(0, 12)) {
  const budget = route.threeD ? BUDGETS.threeD : BUDGETS.non3d;
  const status = route.bytes > budget ? "FAIL" : "ok";
  if (route.bytes > budget) failures += 1;
  console.log(
    `[bundle-budget] ${status.padEnd(4)} ${(route.bytes / KB).toFixed(1).padStart(6)} KB / ${(budget / KB).toFixed(0).padStart(3)} KB  ${route.route}`,
  );
}

if (result.sharedBytes > BUDGETS.shared) {
  console.error(
    `[bundle-budget] FAIL shared JavaScript ${(result.sharedBytes / KB).toFixed(1)} KB exceeds ${(BUDGETS.shared / KB).toFixed(0)} KB.`,
  );
  failures += 1;
}

if (failures > 0) {
  console.error(`[bundle-budget] ${failures} budget(s) exceeded.`);
  process.exit(1);
}
console.log("[bundle-budget] PASS");
