import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";

export const base = "/api/v1/admin/academic-setup";
export const structure = "/api/v1/admin/academic-structure";

export function field(dialog, name) {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return dialog.getByLabel(new RegExp(`^${escaped}\\s*\\*?$`));
}

export async function navigate(page, name) {
  await page.getByRole("button", { name, exact: true }).first().click();
}

export async function open(page, name) {
  const button = page.getByRole("button", { name: `Add ${name}`, exact: true });
  const ready = button.and(page.locator(":enabled"));
  const retry = page
    .getByRole("button", { name: "Retry", exact: true })
    .first();
  await ready.or(retry).first().waitFor();
  if (!(await button.isEnabled())) {
    console.log(`RECOVERY: retrying failed catalogue read before ${name}`);
    await retry.click();
  }
  await ready.click();
  return page.getByRole("dialog", { name: `Add ${name}`, exact: true });
}

export async function save(page, dialog, endpoint, button, method = "POST") {
  const response = page.waitForResponse(
    (item) =>
      new URL(item.url()).pathname === endpoint &&
      item.request().method() === method,
  );
  await dialog.getByRole("button", { name: button, exact: true }).click();
  const result = await response;
  assert.ok(
    result.ok(),
    `${method} ${endpoint}: ${result.status()} ${await result.text()}`,
  );
  const record = await result.json();
  await dialog.waitFor({ state: "hidden" });
  return record;
}

export async function api(page, endpoint, method = "GET") {
  const result = await page.evaluate(
    async ({ endpoint, method }) => {
      const response = await fetch(endpoint, {
        method,
        headers: {
          Authorization: `Bearer ${localStorage.getItem("college-ai-chatbot.access-token")}`,
        },
      });
      return { status: response.status, body: await response.text() };
    },
    { endpoint, method },
  );
  assert.ok(
    result.status >= 200 && result.status < 300,
    `${method} ${endpoint}: ${result.status}`,
  );
  return result.body ? JSON.parse(result.body) : null;
}

export async function remember(settings, records, entity, record) {
  records[entity] = record;
  await fs.writeFile(
    path.join(settings.logDir, `${settings.prefix}-records.json`),
    JSON.stringify(
      { prefix: settings.prefix, user_id: settings.user_id, records },
      null,
      2,
    ),
  );
  console.log(`PASS: browser saved ${entity}`);
}
