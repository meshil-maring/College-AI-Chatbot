import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs/promises";
import { createFixture } from "./fixtures.mjs";
import { journey } from "./journey.mjs";
import { resourceChatJourney } from "./chat_journey.mjs";
import { recoveryJourney } from "./recovery_journey.mjs";

const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);
const require = createRequire(path.join(root, "frontend/package.json"));
const { chromium } = require("playwright-core");
const origin = new URL(process.argv[2] || "http://127.0.0.1:5180");
const backendIndex = process.argv.indexOf("--backend");
const backend =
  backendIndex < 0 ? null : new URL(process.argv[backendIndex + 1]);
if (backend) {
  assert(
    ["127.0.0.1", "localhost"].includes(backend.hostname) &&
      backend.protocol === "http:",
    "Loopback HTTP backend only",
  );
}
assert(
  ["127.0.0.1", "localhost"].includes(origin.hostname) &&
    origin.protocol === "http:",
  "Loopback HTTP UI only",
);
const logDir = path.join(root, "logs/frontend/learning-resource-ui/browser");
await fs.mkdir(logDir, { recursive: true });
const browser = await chromium.launch({ channel: "msedge", headless: true });
try {
  for (const role of ["admin", "faculty", "staff"]) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
      reducedMotion: "reduce",
    });
    const fixture = createFixture(role);
    const errors = [];
    await context.route("**/*", async (route) => {
      const url = new URL(route.request().url());
      if (url.origin !== origin.origin) {
        errors.push(`Blocked non-loopback request: ${url.pathname}`);
        return route.abort();
      }
      if (url.pathname.startsWith("/api/")) {
        if (!backend) return fixture.handle(route);
        const response = await route.fetch({
          url: new URL(url.pathname + url.search, backend).href,
          maxRedirects: 0,
          timeout: 60000,
        });
        return route.fulfill({ response });
      }
      return route.continue();
    });
    await context.addInitScript(
      (role) =>
        localStorage.setItem(
          "college-ai-chatbot.access-token",
          `fixture-${role}`,
        ),
      role,
    );
    const page = await context.newPage();
    page.setDefaultTimeout(backend ? 45000 : 15000);
    page.on("pageerror", (error) => errors.push(error.message));
    try {
      await page.goto(new URL("/login", origin).href, {
        waitUntil: "domcontentloaded",
      });
      await journey(page, role, logDir);
      await resourceChatJourney(page, role, logDir);
      if (backend) await recoveryJourney(page, role, logDir, backend);
      assert.deepEqual(
        fixture.state.errors,
        [],
        "All intercepted HTTP contracts match",
      );
      assert.deepEqual(errors, [], "No page errors or remote requests");
      console.log(
        `PASS ${role}: library/upload/review, resource Ask AI/follow-ups/restored history, responsive layout and focus`,
      );
    } catch (error) {
      await page.screenshot({ path: path.join(logDir, `${role}-failure.png`) });
      await fs.writeFile(
        path.join(logDir, `${role}-failure.txt`),
        await page.locator("body").innerText(),
      );
      throw error;
    } finally {
      await context.unrouteAll({ behavior: "wait" });
      await context.close();
    }
  }
} finally {
  await browser.close();
}
