import path from "node:path";
import assert from "node:assert/strict";
import { checkLayout } from "./journey.mjs";

export async function resourceChatJourney(page, role, logDir) {
  await page
    .getByRole("button", { name: "View Student support handbook" })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Ask AI", exact: true })
    .click();
  const scope = page.getByRole("region", {
    name: "Resource conversation scope",
  });
  await scope
    .getByRole("heading", { name: "Asking about: Student support handbook" })
    .waitFor();
  for (const [index, question] of [
    "Summarize this resource",
    "What does it say about library hours?",
  ].entries()) {
    await page.getByRole("textbox", { name: "Ask a question" }).fill(question);
    await page.getByRole("button", { name: "Send message" }).click();
    await page
      .getByText(/^Fictional resource answer:/)
      .nth(index)
      .waitFor();
  }
  const cards = page
    .getByRole("log", { name: "Chat messages" })
    .locator("article");
  await cards.nth(1).waitFor();
  const savedCards = await cards.allTextContents();
  await checkLayout(page);
  await page.screenshot({
    path: path.join(logDir, `${role}-resource-chat-320.png`),
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.reload();
  await page.getByRole("button", { name: "AI Assistant", exact: true }).click();
  assert.equal(
    await page
      .getByRole("region", { name: "Resource conversation scope" })
      .count(),
    0,
  );
  await page.getByRole("button", { name: /Summarize this resource/ }).click();
  await page
    .getByRole("heading", { name: "Asking about: Student support handbook" })
    .waitFor();
  await cards.nth(1).waitFor();
  assert.deepEqual(
    await cards.allTextContents(),
    savedCards,
    "Reopened history retains the same source cards",
  );
  await page.setViewportSize({ width: 320, height: 800 });
  await checkLayout(page);
  await page.screenshot({
    path: path.join(logDir, `${role}-history-citations-320.png`),
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page
    .getByRole("textbox", { name: "Ask a question" })
    .fill("Tell me more about this resource");
  await page.getByRole("button", { name: "Send message" }).click();
  await page
    .getByText(/^Fictional resource answer:/)
    .nth(2)
    .waitFor();
  await checkLayout(page);
  await page.screenshot({
    path: path.join(logDir, `${role}-resource-chat-restored.png`),
  });
}
