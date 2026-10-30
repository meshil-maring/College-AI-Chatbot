import assert from "node:assert/strict";
import { createServer } from "node:http";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs/promises";
import {
  user,
  catalogue,
  structure,
  registration,
} from "./navigation-fixtures.mjs";

const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../../../",
);
const dist = path.join(root, "frontend/dist");
const logDir = path.join(root, "logs/frontend/academic-navigation");
await fs.mkdir(logDir, { recursive: true });
const require = createRequire(path.join(root, "frontend/package.json"));
const { chromium } = require("playwright-core");
const mime = {
  ".js": "text/javascript",
  ".css": "text/css",
  ".html": "text/html",
  ".svg": "image/svg+xml",
};
const server = createServer(async (request, response) => {
  const pathname = new URL(request.url, "http://localhost").pathname;
  const file = pathname.startsWith("/assets/")
    ? path.resolve(dist, `.${pathname}`)
    : path.join(dist, "index.html");
  if (!file.startsWith(`${dist}${path.sep}`))
    return response.writeHead(403).end();
  try {
    response.writeHead(200, {
      "Content-Type": mime[path.extname(file)] ?? "application/octet-stream",
    });
    response.end(await fs.readFile(file));
  } catch {
    response.writeHead(404).end();
  }
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
});
const page = await context.newPage();
const errors = [];
const unexpectedRequests = [];
page.on("pageerror", (error) => errors.push(error.message));
await context.addInitScript(() =>
  localStorage.setItem(
    "college-ai-chatbot.access-token",
    "local-navigation-fixture",
  ),
);
await context.route("**/*", async (route) => {
  const request = route.request();
  const url = new URL(request.url());
  const fixtures = {
    "/api/v1/auth/me": user,
    "/api/v1/admin/academic-setup": catalogue,
    "/api/v1/admin/academic-structure": structure,
    "/api/v1/admin/academic-registration": registration,
  };
  if (url.pathname.startsWith("/api/")) {
    if (request.method() !== "GET" || !fixtures[url.pathname]) {
      unexpectedRequests.push(`${request.method()} ${url.pathname}`);
      return route.fulfill({
        status: 400,
        json: { detail: "Unexpected local fixture request" },
      });
    }
    return route.fulfill({ json: fixtures[url.pathname] });
  }
  if (url.origin !== origin) return route.abort();
  return route.continue();
});
const academicUrl = (destination) =>
  `${origin}/?view=academic-setup&academic=${destination}`;
const sidebar = page.getByRole("navigation", {
  name: "Academic Setup navigation",
});
async function heading(name) {
  await page.getByRole("heading", { name, exact: true, level: 1 }).waitFor();
}
async function fitsViewport() {
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
    true,
  );
  assert.equal(
    await page.evaluate(() => {
      const flow = document
        .querySelector(".academic-workspace-flow")
        .getBoundingClientRect();
      const header = document
        .querySelector(".admin-topbar")
        .getBoundingClientRect();
      return flow.top >= header.bottom - 1;
    }),
    true,
    "The setup guide must remain below the sticky header",
  );
}

try {
  await page.goto(academicUrl("overview"));
  await heading("Academic Setup");
  await fitsViewport();
  await page.screenshot({
    path: path.join(logDir, "desktop-overview.png"),
    fullPage: true,
  });
  await sidebar
    .getByRole("button", { name: "Subject Options", exact: true })
    .click();
  await heading("Subject Options");
  await page.getByText("Semester 3 subject choices", { exact: true }).waitFor();
  await page.screenshot({
    path: path.join(logDir, "desktop-options.png"),
    fullPage: true,
  });
  assert.match(page.url(), /academic=curriculum-options/);
  await page
    .getByRole("button", { name: "Review and publish curriculum", exact: true })
    .click();
  await heading("Curriculum");
  await page
    .getByRole("button", { name: /Curriculum already published/ })
    .click();
  await heading("Batches");
  await page
    .getByRole("button", { name: "Create academic sections", exact: true })
    .click();
  await heading("Sections");
  await page
    .getByRole("button", { name: "Offer section subjects", exact: true })
    .click();
  await heading("Academic Offerings");
  await page
    .getByRole("button", { name: "Assign students to sections", exact: true })
    .click();
  await heading("Student Enrollment");
  await page.goBack();
  await heading("Academic Offerings");
  await page.goForward();
  await heading("Student Enrollment");
  await page.reload();
  await heading("Student Enrollment");
  await sidebar
    .getByRole("button", { name: "Academic Years", exact: true })
    .click();
  await heading("Academic Calendar");
  await page.getByRole("tab", { name: "Semesters", exact: true }).click();
  assert.match(page.url(), /academic=terms/);
  await page.getByRole("tab", { name: "Important Dates", exact: true }).click();
  await page.goBack();
  assert.equal(
    await page
      .getByRole("tab", { name: "Semesters" })
      .getAttribute("aria-selected"),
    "true",
  );
  await page
    .getByRole("button", { name: "Open administrator profile" })
    .click();
  await page.reload();
  assert.doesNotMatch(page.url(), /view=/);
  await page.goBack();
  await heading("Academic Calendar");
  console.log(
    "PASS: guided destinations, calendar tabs, refresh, browser Back/Forward and profile",
  );

  for (const width of [1024, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(academicUrl("overview"));
    await heading("Academic Setup");
    await fitsViewport();
    await page.screenshot({
      path: path.join(logDir, `${width}-overview.png`),
      fullPage: true,
    });
    if (width <= 760)
      await page
        .getByRole("button", { name: "Toggle navigation", exact: true })
        .click();
    await sidebar
      .getByRole("button", { name: "Subject Options", exact: true })
      .click();
    await heading("Subject Options");
    await fitsViewport();
    assert.equal(
      await page
        .getByRole("tab", { name: "Subject Options" })
        .evaluate((tab) => {
          const bounds = tab.parentElement.getBoundingClientRect();
          const selected = tab.getBoundingClientRect();
          return (
            selected.left >= bounds.left - 1 &&
            selected.right <= bounds.right + 1
          );
        }),
      true,
    );
    await page.screenshot({
      path: path.join(logDir, `${width}-options.png`),
      fullPage: true,
    });
    if (width <= 760)
      assert.equal(
        await page
          .getByRole("button", { name: "Toggle navigation" })
          .getAttribute("aria-expanded"),
        "false",
      );
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(unexpectedRequests, []);
  console.log(
    "PASS: desktop, tablet, 390px and 320px reflow; mobile sidebar; no backend writes or page errors",
  );
  await fs.writeFile(
    path.join(logDir, "result.json"),
    JSON.stringify({ passed: true, errors, unexpectedRequests }, null, 2),
  );
} catch (error) {
  await fs.writeFile(
    path.join(logDir, "failure.txt"),
    await page.locator("body").innerText(),
  );
  await page.screenshot({
    path: path.join(logDir, "failure.png"),
    fullPage: true,
  });
  throw error;
} finally {
  await browser.close();
  await new Promise((resolve) => server.close(resolve));
}
