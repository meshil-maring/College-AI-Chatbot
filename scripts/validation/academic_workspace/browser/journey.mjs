import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs/promises";
import { createCatalogue } from "./catalogue.mjs";
import { createCurriculum } from "./curriculum.mjs";
import { createDelivery } from "./delivery.mjs";
import { checkSessions, login } from "./session.mjs";

const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../../../",
);
const require = createRequire(path.join(root, "frontend/package.json"));
const { chromium } = require("playwright-core");
let input = "";
for await (const chunk of process.stdin) input += chunk;
const settings = JSON.parse(input);
const browser = await chromium.launch({ channel: "chrome", headless: true });
console.log("START: headless browser launched");
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
});
const page = await context.newPage();
page.setDefaultTimeout(60_000);
const errors = [];
const records = settings.records ?? {};
page.on("pageerror", (error) => errors.push(error.message));
page.on("response", async (response) => {
  const endpoint = new URL(response.url()).pathname;
  if (endpoint.startsWith("/api/v1/admin/academic") && !response.ok())
    console.log(
      `ACADEMIC HTTP ${response.status()}: ${endpoint} ${await response.text()}`,
    );
});
try {
  await page.clock.install();
  await login(page, settings);
  console.log("PASS: real password login and verified administrator workspace");
  await page
    .getByRole("button", { name: "Academic Setup", exact: true })
    .first()
    .click();
  await page
    .getByRole("heading", { name: "Academic Setup", exact: true })
    .waitFor();
  console.log("PASS: real academic workspace loads");
  if (!records.academic_offerings) {
    if (!records.courses) await createCatalogue(page, settings, records);
    await createCurriculum(page, settings, records);
    await createDelivery(page, settings, records);
  }
  await fs.writeFile(
    path.join(settings.logDir, "workspace-snapshot.txt"),
    await page.locator("body").innerText(),
  );
  await page.screenshot({
    path: path.join(settings.logDir, "workspace.png"),
    fullPage: true,
  });
  await checkSessions(page, context, settings, records);
  assert.deepEqual(errors, []);
  await fs.writeFile(
    path.join(settings.logDir, `${settings.prefix}-result.json`),
    JSON.stringify(
      { status: "passed", prefix: settings.prefix, pageErrors: errors },
      null,
      2,
    ),
  );
} catch (error) {
  await fs.writeFile(
    path.join(settings.logDir, "failure-snapshot.txt"),
    await page.locator("body").innerText(),
  );
  await page.screenshot({
    path: path.join(settings.logDir, "failure.png"),
    fullPage: true,
  });
  throw new Error(String(error).replaceAll(settings.password, "[REDACTED]"));
} finally {
  await browser.close();
}
