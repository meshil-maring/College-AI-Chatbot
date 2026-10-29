import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";
import fs from "node:fs/promises";

const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);
const frontend = path.join(root, "frontend");
const require = createRequire(path.join(frontend, "package.json"));
const { createServer } = await import(
  pathToFileURL(require.resolve("vite")).href
);
const { chromium } = require("playwright-core");
let input = "";
for await (const chunk of process.stdin) input += chunk;
const settings = JSON.parse(input);
const backend = new URL(settings.backend);
assert.equal(backend.hostname, "127.0.0.1");
const directory = path.join(
  root,
  "logs/frontend/live-chat-acceptance",
  settings.run,
);
await fs.mkdir(directory, { recursive: true });
const server = await createServer({
  root: frontend,
  server: {
    host: "127.0.0.1",
    port: 0,
    hmr: false,
    proxy: { "/api": { target: backend.origin, changeOrigin: true } },
  },
});
let browser;
try {
  await server.listen();
  const origin = `http://127.0.0.1:${server.httpServer.address().port}`;
  browser = await chromium.launch({ channel: "msedge", headless: true });
  for (const role of ["public", "admin", "staff", "faculty", "student"]) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
    });
    const page = await context.newPage();
    page.setDefaultTimeout(90_000);
    try {
      if (role === "public") {
        await page.goto(`${origin}/public-chat/${settings.institutionCode}`);
        const restricted = await page.request.post(
          `${origin}/api/v1/chat/public`,
          {
            data: {
              institution_code: settings.institutionCode,
              message:
                "Which room is used for the college's fictional staff workshop, and what must participants bring?",
            },
          },
        );
        assert.equal(restricted.status(), 200);
        const projected = JSON.stringify(await restricted.json());
        assert(
          !projected.includes("Cedar") &&
            !projected.includes("blue notebook") &&
            !projected.includes(`Chat acceptance ${settings.run}`),
          "Anonymous response exposed restricted evidence",
        );
        console.log(
          "PASS: anonymous live retrieval does not expose the restricted test resource",
        );
      } else {
        await page.goto(`${origin}/login/${role}`);
        await page
          .getByLabel("Email, Register Number or University Roll Number")
          .fill(settings.accounts[role].email);
        await page
          .getByLabel("Password", { exact: true })
          .fill(settings.accounts[role].password);
        await page
          .getByRole("button", { name: "Sign in", exact: true })
          .click();
        await page
          .getByRole("button", { name: "AI Assistant", exact: true })
          .first()
          .click();
      }
      const question =
        "Briefly summarize the hostel guest policy for this college.";
      const isPublic = role === "public";
      const endpoint = isPublic
        ? "/api/v1/chat/public"
        : "/api/v1/generation/chat";
      const reply = page.waitForResponse(
        (response) =>
          new URL(response.url()).pathname === endpoint &&
          response.request().method() === "POST",
      );
      await page
        .getByRole("textbox", {
          name: isPublic ? "Ask a public college question" : "Ask a question",
        })
        .fill(question);
      await page
        .getByRole("button", {
          name: isPublic ? "Send" : "Send message",
          exact: true,
        })
        .click();
      const response = await reply;
      assert.equal(response.status(), 200, `${role} live response failed`);
      const body = await response.json();
      assert(body.sources.length > 0, `${role} reply has no sources`);
      assert(
        /\b(sample|draft|illustrative|unapproved)\b/i.test(body.answer),
        `${role} answer lost the uploaded document's qualification`,
      );
      const quotes = page.locator("blockquote");
      await quotes.first().waitFor();
      const savedQuotes = await quotes.allTextContents();
      assert.equal(savedQuotes.length, body.sources.length);
      await page.reload();
      if (!isPublic) {
        await page
          .getByRole("button", { name: "AI Assistant", exact: true })
          .first()
          .click();
        await page
          .getByRole("button", {
            name: new RegExp(question.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")),
          })
          .click();
      }
      await quotes.first().waitFor();
      assert.deepEqual(
        await quotes.allTextContents(),
        savedQuotes,
        `${role} restored citations changed`,
      );
      await page.setViewportSize({ width: 320, height: 800 });
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
        `${role} overflows mobile`,
      );
      await page.screenshot({
        path: path.join(directory, `${role}-citations-320.png`),
        fullPage: true,
      });
      console.log(
        `PASS: ${role} real browser login/chat, source cards, reload and 320px layout`,
      );
    } catch (failure) {
      await page.screenshot({
        path: path.join(directory, `${role}-failure.png`),
        fullPage: true,
      });
      let message = String(failure);
      for (const account of Object.values(settings.accounts))
        message = message.replaceAll(account.password, "[REDACTED]");
      throw new Error(message);
    } finally {
      await context.close();
    }
  }
} finally {
  await browser?.close();
  await server.close();
}
