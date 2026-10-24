/* End-to-end product verification with the existing Playwright dependency and a local browser. */
/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("@playwright/test");

const BASE = process.env.ANIMUS_BASE_URL || "http://localhost:3000";
const OUT = path.resolve(__dirname, "../../docs/animus");
const BROWSERS = [
  process.env.CHROME_PATH,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
].filter(Boolean);
const executablePath = BROWSERS.find((candidate) => fs.existsSync(candidate));
let browser;

async function main() {
  if (!executablePath) throw new Error("No local Chrome/Edge executable found");
  fs.mkdirSync(OUT, { recursive: true });
  browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`);
  });
  page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));

  await page.goto(`${BASE}/animus`, { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(OUT, "01-landing.png"), fullPage: false });

  await page.fill('[data-testid="animus-intention"]', "a white castle above a dark ocean at dusk");
  await page.click('[data-testid="enter-studio"]');
  await page.waitForURL(/\/animus\/studio\/ast_/, { timeout: 45000 });
  await page.waitForSelector('[data-testid="animus-scene"]');
  await page.waitForTimeout(2500);
  const initialVersion = (await page.textContent('[data-testid="studio-version"]')).trim();
  await page.waitForFunction(
    () => document.querySelector('[data-testid="studio-connection"]')?.textContent?.includes("live"),
    undefined,
    { timeout: 15000 },
  );
  await page.screenshot({ path: path.join(OUT, "02-studio-initial.png") });

  await page.fill('[data-testid="studio-prompt"]', "make the sky deep violet");
  await page.press('[data-testid="studio-prompt"]', "Enter");
  await page.waitForFunction(
    () => document.querySelector('[data-testid="studio-version"]')?.textContent === "v2",
    undefined,
    { timeout: 30000 },
  );
  await page.waitForTimeout(700);
  await page.screenshot({ path: path.join(OUT, "03-studio-corrected.png") });

  await page.locator('[data-testid="entity-row"]').first().click();
  await page.getByRole("button", { name: "Lock element" }).click();
  await page.waitForFunction(
    () => document.querySelector('[data-testid="studio-version"]')?.textContent === "v3",
    undefined,
    { timeout: 30000 },
  );

  await page.getByRole("button", { name: /Explore 3 variations/ }).click();
  await page.waitForSelector('[data-testid="candidate-card"]', { timeout: 30000 });
  await page.waitForTimeout(900);
  const candidateCount = await page.locator('[data-testid="candidate-card"]').count();
  const candidateCopy = await page.locator('[data-testid="candidate-card"]').first().innerText();
  if (!candidateCopy.includes("kept")) throw new Error("candidates did not report preserved locked content");
  await page.screenshot({ path: path.join(OUT, "04-studio-candidates.png") });

  await page.reload({ waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="animus-scene"]');
  await page.waitForFunction(
    (expected) => document.querySelectorAll('[data-testid="candidate-card"]').length === expected,
    candidateCount,
    { timeout: 15000 },
  );
  const reloadedCandidateCount = await page.locator('[data-testid="candidate-card"]').count();
  if (reloadedCandidateCount !== candidateCount) {
    throw new Error("candidates disappeared after a reload");
  }

  await page
    .locator('[data-testid="candidate-card"]')
    .first()
    .getByRole("button", { name: "Keep this" })
    .click();
  await page.waitForFunction(
    () => document.querySelector('[data-testid="studio-version"]')?.textContent === "v4",
    undefined,
    { timeout: 30000 },
  );

  await page.getByRole("button", { name: "Undo" }).first().click();
  await page.waitForFunction(
    () => document.querySelector('[data-testid="studio-version"]')?.textContent === "v3",
    undefined,
    { timeout: 30000 },
  );

  await page.click('[data-testid="inspector-tab-history"]');
  await page.fill('[data-testid="branch-name"]', "variation");
  await page.getByRole("button", { name: "Create", exact: true }).click();
  await page.waitForFunction(
    () => document.querySelector('[data-testid="studio-branch"]')?.textContent === "variation",
    undefined,
    { timeout: 30000 },
  );
  await page.locator('[data-testid="branch-switch"]').first().click();
  await page.waitForFunction(
    () => document.querySelector('[data-testid="studio-branch"]')?.textContent === "Main",
    undefined,
    { timeout: 30000 },
  );
  const branchRoundTrip = true;

  await page.getByRole("button", { name: "Save world" }).first().click();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(OUT, "05-studio-saved.png") });

  await page.reload({ waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="animus-scene"]');
  await page.waitForTimeout(1800);
  const reloadedVersion = (await page.textContent('[data-testid="studio-version"]')).trim();
  const studioUrl = page.url();

  await page.goto(`${BASE}/animus/worlds`, { waitUntil: "networkidle" });
  const worldCards = await page.getByRole("button", { name: "Open studio" }).count();
  if (worldCards < 1) throw new Error("saved world did not appear in the world library");
  await page.getByRole("button", { name: "Open studio" }).first().click();
  await page.waitForURL(/\/animus\/studio\/ast_/, { timeout: 45000 });
  await page.waitForSelector('[data-testid="animus-scene"]');
  const openedWorldVersion = (await page.textContent('[data-testid="studio-version"]')).trim();

  await page.goto(`${BASE}/animus/worlds`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /^Delete / }).first().click();
  await page.getByRole("button", { name: /^Confirm deleting / }).first().click();
  await page.waitForFunction(
    (expected) => document.querySelectorAll("button").length > 0
      && [...document.querySelectorAll("button")].filter((button) => button.textContent?.trim() === "Open studio").length === expected,
    worldCards - 1,
    { timeout: 15000 },
  );
  const worldCardsAfterDelete = await page.getByRole("button", { name: "Open studio" }).count();
  if (worldCardsAfterDelete !== worldCards - 1) throw new Error("world delete was not confirmed");
  await page.screenshot({ path: path.join(OUT, "05b-worlds-after-delete.png") });

  const missingPage = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await missingPage.goto(`${BASE}/animus/studio/ast_missing_404`, { waitUntil: "networkidle" });
  const missingCopy = await missingPage.locator("body").innerText();
  await missingPage.close();
  if (!missingCopy.includes("This studio does not exist")) {
    throw new Error("missing studio did not show the typed 404 state");
  }

  await page.goto(`${BASE}/imagina/animus`, { waitUntil: "networkidle" });
  const legacyRedirect = new URL(page.url()).pathname;

  await page.goto(`${BASE}/animus/about`, { waitUntil: "networkidle" });
  const aboutCopy = await page.locator("body").innerText();
  const normalizedAbout = aboutCopy.toLowerCase();
  if (!normalizedAbout.includes("claim ceiling l1") || !aboutCopy.includes("DISABLED")) {
    throw new Error("about page did not expose the capability boundary");
  }

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto(studioUrl, { waitUntil: "networkidle" });
  await mobile.waitForSelector('[data-testid="animus-scene"]');
  await mobile.waitForTimeout(1200);
  const mobileOverflow = await mobile.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  await mobile.screenshot({ path: path.join(OUT, "06-studio-mobile.png"), fullPage: false });
  if (mobileOverflow > 2) throw new Error(`mobile layout overflows by ${mobileOverflow}px`);
  await mobile.close();

  const result = {
    base: BASE,
    studio_url: studioUrl,
    initial_version: initialVersion,
    candidate_count: candidateCount,
    reloaded_candidate_count: reloadedCandidateCount,
    branch_round_trip: branchRoundTrip,
    reloaded_version: reloadedVersion,
    world_cards: worldCards,
    world_cards_after_delete: worldCardsAfterDelete,
    opened_world_version: openedWorldVersion,
    missing_studio_state: "typed_404",
    legacy_redirect: legacyRedirect,
    mobile_overflow_px: mobileOverflow,
    console_errors: errors,
    screenshots: fs.readdirSync(OUT).sort(),
  };
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
  if (errors.length) process.exitCode = 1;
}

main().catch(async (error) => {
  console.error(error);
  process.exitCode = 1;
  if (browser) await browser.close().catch(() => undefined);
});
