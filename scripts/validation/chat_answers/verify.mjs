import assert from "node:assert/strict";
import { createRequire } from "node:module";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

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
const evidence = path.join(root, "logs/frontend/answer-formatting/browser");
await fs.mkdir(evidence, { recursive: true });
const recorded = JSON.parse(
  await fs.readFile(
    path.join(root, "logs/backend/answer-formatting/live-response.json"),
    "utf8",
  ),
);
assert.equal(recorded.http_status, 200);
assert(
  recorded.response.answer.includes("\n"),
  "The live API must retain Markdown line breaks",
);

const oldAnswer =
  "This is a draft sample, not an officially approved college policy. Here are its key points: " +
  "1. **Admission and Room Allocation**:- Complete the hostel application and submit required documents. - Obtain approval before changing rooms or beds. " +
  "2. **Keys and Access**:- Do not copy room keys or lend them to unauthorized persons. " +
  "3. **Guest Policy**:- Overnight guests require explicit permission. " +
  "4. **Entry Timings**:- The sample entry time is 9:00 PM; verify the actual college timing. " +
  "5. **Disciplinary Actions**:- Reviews must follow the institution's approved procedures. " +
  "6. **Maintenance and Contacts**:- Report issues to the hostel office.";

const browser = await chromium.launch({ channel: "msedge", headless: true });
try {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 1000 },
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await context.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== origin.origin) {
      errors.push(`Unexpected remote request: ${url.pathname}`);
      return route.abort();
    }
    if (url.pathname === "/api/v1/chat/public") {
      return route.fulfill({ json: recorded.response });
    }
    return route.continue();
  });
  await context.addInitScript((answer) => {
    const key = "college-ai-chatbot.public-chat.v2:QUEST123";
    if (localStorage.getItem(key)) return;
    localStorage.setItem(
      key,
      JSON.stringify({
        version: 2,
        conversation: {
          id: "formatting-verification",
          institutionCode: "QUEST123",
          createdAt: 1,
          updatedAt: 2,
          messages: [
            {
              id: "question",
              role: "user",
              content: "What are the hostel rules and regulations?",
              createdAt: 1,
            },
            {
              id: "answer",
              role: "assistant",
              content: answer,
              status: "success",
              sources: [],
              createdAt: 2,
            },
          ],
        },
      }),
    );
  }, oldAnswer);
  await page.goto(new URL("/public-chat/QUEST123", origin).href, {
    waitUntil: "domcontentloaded",
  });
  const restored = page.locator(".chat-answer").first();
  await restored.locator("ol > li").first().waitFor();
  assert.equal(await restored.locator(":scope > ol > li").count(), 6);
  assert.equal(await restored.locator("ul > li").count(), 7);
  assert(!(await restored.innerText()).includes("**"));

  async function screenshot(name, width) {
    await page.setViewportSize({ width, height: 1000 });
    const log = page.getByRole("region", { name: "Public chat conversation" });
    await log.evaluate((element) => {
      element.scrollTop = 0;
    });
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    assert.equal(overflow, false, `No horizontal overflow at ${width}px`);
    await page.screenshot({ path: path.join(evidence, name), fullPage: true });
  }
  await screenshot("restored-desktop.png", 1280);
  await screenshot("restored-mobile.png", 320);

  await page.setViewportSize({ width: 1280, height: 1000 });
  await page
    .getByLabel("Ask a public college question")
    .fill("Give a clearly formatted summary of the hostel rules.");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  const fresh = page.locator(".chat-answer").last();
  await fresh.getByRole("heading").first().waitFor();
  assert((await fresh.locator("ul > li").count()) > 2);
  assert.equal(await page.locator(".chat-answer").count(), 2);
  await screenshot("new-answer-desktop.png", 1280);
  await screenshot("new-answer-mobile.png", 320);
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.locator(".chat-answer").nth(1).waitFor();
  assert.equal(await page.locator(".chat-answer").count(), 2);
  assert.deepEqual(errors, []);
  await context.unrouteAll({ behavior: "wait" });
  await context.close();
  console.log(
    "PASS: restored/new Markdown answers, headings/lists, history reload, desktop/320px layouts",
  );
} finally {
  await browser.close();
}
