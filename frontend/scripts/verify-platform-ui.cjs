#!/usr/bin/env node
/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * Route-level UI audit for the IMAGINA platform.
 *
 * Checks every static route for HTTP failures, console errors, horizontal
 * overflow, sub-11px visible text, and undersized interactive targets.
 * Exits nonzero when a route fails to load, throws, or overflows.
 */
const fs = require("node:fs");
const { chromium } = require("@playwright/test");

const BASE = process.env.PLATFORM_BASE_URL || "http://127.0.0.1:3000";
const BROWSERS = [
  process.env.CHROME_PATH,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
].filter(Boolean);
const executablePath = BROWSERS.find((candidate) => fs.existsSync(candidate));
const ROUTES = [
  "/",
  "/session",
  "/replay",
  "/profile",
  "/science",
  "/method",
  "/experiments",
  "/multimodal",
  "/datasets",
  "/research",
  "/research/operator",
  "/research/design",
  "/research/participant",
  "/research/synthetic-demo",
  "/research/measurement",
  "/research/design-simulation",
  "/research/analysis",
  "/research/eeg-validation",
  "/imagina",
  "/imagina/live",
  "/imagina/showcase",
  "/animus",
  "/animus/imagine",
  "/animus/about",
  "/animus/worlds",
  "/animus/profile",
];

async function audit(page, route) {
  const consoleErrors = [];
  const failedRequests = [];
  const onConsole = (message) => {
    if (message.type() === "error") {
      const text = message.text();
      if (!text.includes("favicon")) consoleErrors.push(text.slice(0, 240));
    }
  };
  const onFailed = (request) => {
    const failure = request.failure();
    if (failure && !request.url().includes("favicon")) {
      failedRequests.push(`${request.url()} · ${failure.errorText}`);
    }
  };
  page.on("console", onConsole);
  page.on("requestfailed", onFailed);

  let status = 0;
  try {
    const response = await page.goto(`${BASE}${route}`, { waitUntil: "domcontentloaded", timeout: 45_000 });
    status = response ? response.status() : 0;
  } catch (error) {
    return { route, status: "NAVIGATION", error: String(error).slice(0, 200), consoleErrors, failedRequests };
  }

  await page.waitForTimeout(900);
  const metrics = await page.evaluate(() => {
    const visible = (element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
    };
    const smallText = [];
    for (const element of document.querySelectorAll("body *")) {
      if (!visible(element)) continue;
      const ownText = Array.from(element.childNodes)
        .filter((node) => node.nodeType === Node.TEXT_NODE)
        .map((node) => node.textContent?.trim() || "")
        .join(" ")
        .trim();
      if (!ownText) continue;
      const size = Number.parseFloat(getComputedStyle(element).fontSize);
      if (size > 0 && size < 10.9) {
        smallText.push({
          tag: element.tagName.toLowerCase(),
          text: ownText.slice(0, 60),
          size: Math.round(size * 10) / 10,
        });
      }
    }
    const smallTargets = [];
    for (const element of document.querySelectorAll("button, a[role='button'], [role='button']")) {
      if (!visible(element)) continue;
      const rect = element.getBoundingClientRect();
      if (rect.width < 24 || rect.height < 24) {
        smallTargets.push({
          tag: element.tagName.toLowerCase(),
          label: (element.getAttribute("aria-label") || element.textContent || "").trim().slice(0, 50),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        });
      }
    }
    return {
      h1: document.querySelectorAll("h1").length,
      title: document.title,
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      smallText: smallText.slice(0, 8),
      smallTargets: smallTargets.slice(0, 8),
      smallTargetCount: smallTargets.length,
    };
  }).catch(() => null);

  page.off("console", onConsole);
  page.off("requestfailed", onFailed);
  return { route, status, ...metrics, consoleErrors, failedRequests };
}

(async () => {
  if (!executablePath) throw new Error("No local Chrome/Edge executable found");
  const browser = await chromium.launch({ headless: true, executablePath });
  const context = await browser.newContext({
    viewport: { width: Number(process.env.PLATFORM_WIDTH || 1440), height: Number(process.env.PLATFORM_HEIGHT || 900) },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  const results = [];

  for (const route of ROUTES) {
    const result = await audit(page, route);
    results.push(result);
    const badStatus = result.status !== 200;
    const overflow = (result.overflow || 0) > 1;
    const smallText = (result.smallText?.length || 0) > 0;
    const smallTargets = (result.smallTargetCount || 0) > 0;
    const flag = badStatus || overflow || smallText || smallTargets || result.consoleErrors?.length ? "FAIL" : "ok  ";
    console.log(
      `${flag} ${String(result.status).padEnd(4)} ${route.padEnd(34)} h1=${result.h1 ?? "?"} ` +
        `overflow=${result.overflow ?? "?"}px text<11=${result.smallText?.length ?? "?"} targets<24=${result.smallTargetCount ?? "?"}`,
    );
    for (const item of result.smallText || []) console.log(`       text ${item.size}px <${item.tag}> ${item.text}`);
    for (const item of result.smallTargets || []) console.log(`       target ${item.width}x${item.height} <${item.tag}> ${item.label}`);
    for (const item of result.consoleErrors || []) console.log(`       console: ${item}`);
    for (const item of result.failedRequests || []) console.log(`       request: ${item}`);
  }

  await browser.close();
  const failed = results.filter(
    (result) =>
      result.status !== 200 ||
      (result.overflow || 0) > 1 ||
      (result.smallText?.length || 0) > 0 ||
      (result.smallTargetCount || 0) > 0 ||
      result.consoleErrors?.length,
  );
  console.log(`\n${results.length - failed.length}/${results.length} routes clean.`);
  if (failed.length) process.exitCode = 1;
})();
