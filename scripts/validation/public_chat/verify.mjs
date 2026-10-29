import assert from "node:assert/strict";
import { createRequire } from "node:module";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { startFixture } from "./server.mjs";

const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);
const require = createRequire(path.join(root, "frontend/package.json"));
const { chromium } = require("playwright-core");
const origin = new URL(process.argv[2] || "http://127.0.0.1:5180");
assert(
  ["127.0.0.1", "localhost"].includes(origin.hostname) &&
    origin.protocol === "http:",
);
const logDir = path.join(root, "logs/frontend/public-chat-recovery/browser");
await fs.mkdir(logDir, { recursive: true });
const fixture = await startFixture(origin);
const browser = await chromium.launch({ channel: "msedge", headless: true });
try {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    reducedMotion: "reduce",
  });
  const errors = [];
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (![origin.origin, fixture.url.origin].includes(url.origin)) {
      errors.push(`Blocked external request: ${url.pathname}`);
      return route.abort();
    }
    if (url.pathname === "/api/v1/chat/public") {
      return route.continue({ url: new URL(url.pathname, fixture.url).href });
    }
    if (url.pathname.startsWith("/api/")) {
      errors.push(`Unexpected API request: ${url.pathname}`);
      return route.fulfill({ status: 404, json: {} });
    }
    return route.continue();
  });
  const page = await context.newPage();
  page.setDefaultTimeout(45000);
  page.on("pageerror", (error) => errors.push(error.message));
  const ask = async (question) => {
    await page.getByLabel("Ask a public college question").fill(question);
    await page.getByRole("button", { name: "Send", exact: true }).click();
  };
  const screenshot = async (name) => {
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth + 1,
    );
    assert.equal(
      overflow,
      false,
      "Public recovery does not overflow horizontally",
    );
    await page.getByRole("alert").scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(logDir, name), fullPage: true });
  };
  try {
    await page.goto(new URL("/public-chat/PUBLIC-TEST", origin).href, {
      waitUntil: "domcontentloaded",
    });
    await ask("Slow body question");
    await page
      .getByRole("alert")
      .filter({ hasText: "took too long" })
      .waitFor();
    assert.equal(
      fixture.requests.length,
      1,
      "A timed-out body is not automatically retried",
    );
    await page.setViewportSize({ width: 320, height: 800 });
    await screenshot("timeout-320.png");
    await page.reload();
    await page
      .getByRole("alert")
      .filter({ hasText: "previous request was interrupted" })
      .waitFor();
    await page.getByRole("button", { name: "Retry", exact: true }).click();
    await page
      .getByText("Public reply: Slow body question", { exact: true })
      .waitFor();
    assert.equal(
      await page.getByText("Slow body question", { exact: true }).count(),
      1,
    );
    assert.deepEqual(fixture.requests[0], fixture.requests[1]);
    console.log(
      "PASS: real streamed body times out; reload preserves one question and explicit retry succeeds",
    );

    await ask("Busy question");
    const waiting = page.getByRole("button", { name: /^Retry in \d+s$/ });
    await waiting.waitFor();
    assert.equal(await waiting.isDisabled(), true);
    await screenshot("retry-delay-320.png");
    await page.waitForFunction(() =>
      [...document.querySelectorAll("button")].some(
        (button) => button.textContent === "Retry" && !button.disabled,
      ),
    );
    assert.equal(
      fixture.requests.length,
      3,
      "The retry timer only unlocks the button",
    );
    await page.getByRole("button", { name: "Retry", exact: true }).click();
    await page
      .getByText("Public reply: Busy question", { exact: true })
      .waitFor();
    assert.equal(
      await page.getByText("Busy question", { exact: true }).count(),
      1,
    );
    console.log(
      "PASS: Retry-After disables retries, waits, and never resends automatically",
    );

    await page.setViewportSize({ width: 1440, height: 1000 });
    const started = fixture.waitForQuestion("Stopped question");
    await ask("Stopped question");
    await started;
    await page
      .getByRole("button", { name: "Stop waiting", exact: true })
      .click();
    await page
      .getByRole("alert")
      .filter({ hasText: "Your question is saved" })
      .waitFor();
    await screenshot("stopped-desktop.png");
    await page.getByRole("button", { name: "Retry", exact: true }).click();
    await page
      .getByText("Public reply: Stopped question", { exact: true })
      .waitFor();
    assert.equal(
      await page.getByText("Stopped question", { exact: true }).count(),
      1,
    );
    assert.equal(fixture.requests.length, 6);
    assert.deepEqual(errors, []);
    console.log(
      "PASS: Stop waiting aborts the browser request; same-question retry succeeds without a duplicate bubble",
    );
    console.log(
      "PASS: public flow sends no credentials and contacts no authentication API or external provider",
    );
  } catch (error) {
    await page.screenshot({
      path: path.join(logDir, "failure.png"),
      fullPage: true,
    });
    await fs.writeFile(
      path.join(logDir, "failure.txt"),
      await page.locator("body").innerText(),
    );
    throw error;
  } finally {
    await context.close();
  }
} finally {
  await browser.close();
  await fixture.close();
}
