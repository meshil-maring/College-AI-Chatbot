import assert from "node:assert/strict";
import { field, api, navigate, open } from "./helpers.mjs";

export async function login(page, settings) {
  await page.goto(`${settings.baseURL}/login/admin`);
  await page
    .getByLabel("Email, Register Number or University Roll Number")
    .fill(settings.email);
  await page.getByLabel("Password", { exact: true }).fill(settings.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page
    .getByRole("button", { name: "Academic Setup", exact: true })
    .first()
    .waitFor();
}

async function advanceToRenewal(page) {
  const delay = await page.evaluate(() =>
    Math.max(
      0,
      Number(localStorage.getItem("college-ai-chatbot.session-expires-at")) -
        Date.now() -
        60_000,
    ),
  );
  const response = page.waitForResponse(
    (item) =>
      new URL(item.url()).pathname === "/api/v1/auth/refresh" &&
      item.request().method() === "POST",
  );
  await page.clock.fastForward(delay + 100);
  return response;
}

export async function checkSessions(page, context, settings, records) {
  await navigate(page, "Program Semesters");
  let dialog = await open(page, "Program Semester");
  await field(dialog, "Program").selectOption(records.programs.program_id);
  await field(dialog, "Semester Name").fill("Unsaved renewal draft");
  const oldToken = await page.evaluate(() =>
    localStorage.getItem("college-ai-chatbot.access-token"),
  );
  const response = await advanceToRenewal(page);
  assert.ok(response.ok(), `Real token renewal failed: ${response.status()}`);
  await page.waitForFunction((old) => {
    const current = localStorage.getItem("college-ai-chatbot.access-token");
    return Boolean(current && current !== old);
  }, oldToken);
  dialog = page.getByRole("dialog", {
    name: "Add Program Semester",
    exact: true,
  });
  assert.equal(
    await field(dialog, "Semester Name").inputValue(),
    "Unsaved renewal draft",
  );
  console.log(
    "PASS: real provider renewal preserves the unsaved academic draft",
  );
  await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
  await page
    .getByRole("button", { name: "Discard Changes", exact: true })
    .click();

  await api(page, "/api/v1/auth/logout-all", "POST");
  const expired = await advanceToRenewal(page);
  assert.equal(expired.status(), 401);
  await page.getByRole("button", { name: "Sign in", exact: true }).waitFor();
  assert.ok(
    await page.evaluate(
      () =>
        localStorage.getItem("college-ai-chatbot.access-token") === null &&
        localStorage.getItem("college-ai-chatbot.refresh-token") === null,
    ),
  );
  console.log(
    "PASS: revoked refresh session returns to login and clears saved tokens",
  );

  await login(page, settings);
  await page.reload();
  await page
    .getByRole("button", { name: "Academic Setup", exact: true })
    .first()
    .waitFor();
  console.log("PASS: password re-login and authenticated reload recovery");
  const other = await context.newPage();
  await other.goto(`${settings.baseURL}/login/admin`);
  await other
    .getByRole("button", { name: "Academic Setup", exact: true })
    .first()
    .waitFor();
  await page
    .getByRole("button", { name: /Sign out/i })
    .first()
    .click();
  await other.getByRole("button", { name: "Sign in", exact: true }).waitFor();
  console.log("PASS: sign-out clears the second browser tab");
  await other.close();
}
