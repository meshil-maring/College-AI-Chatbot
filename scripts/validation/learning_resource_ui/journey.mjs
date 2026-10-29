import assert from "node:assert/strict";
import path from "node:path";

export async function checkLayout(page) {
  const overflow = await page.evaluate(() => {
    const dialog = document.querySelector("dialog[open]");
    return {
      page: document.documentElement.scrollWidth > innerWidth + 1,
      drawer: dialog ? dialog.scrollWidth > dialog.clientWidth + 1 : false,
    };
  });
  assert.deepEqual(
    overflow,
    { page: false, drawer: false },
    "No page or drawer horizontal overflow",
  );
}
export async function journey(page, role, logDir) {
  await page
    .getByRole("button", { name: "Learning Resources", exact: true })
    .click();
  await page
    .getByRole("button", { name: "View Student support handbook" })
    .waitFor();
  await checkLayout(page);
  await page.screenshot({
    path: path.join(logDir, `${role}-desktop.png`),
    fullPage: true,
  });
  await page.setViewportSize({ width: 1024, height: 900 });
  await checkLayout(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await checkLayout(page);
  await page.screenshot({
    path: path.join(logDir, `${role}-mobile.png`),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Add resource" }).click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByRole("textbox", { name: "Title" })
    .fill("Library access and borrowing rules for students and teachers");
  await dialog
    .getByRole("textbox", { name: "Description" })
    .fill("Fictional material for local browser verification.");
  await dialog.getByRole("radio", { name: "Public", exact: false }).check();
  await dialog
    .getByRole("radio", { name: "Selected roles", exact: false })
    .check();
  await dialog.getByRole("checkbox", { name: "Students" }).check();
  await dialog.getByRole("checkbox", { name: "Teachers" }).check();
  await page.keyboard.press("Escape");
  const warning = page.getByRole("alertdialog");
  assert(
    await warning
      .getByRole("button", { name: "Keep editing" })
      .evaluate((button) => button === document.activeElement),
  );
  await warning.getByRole("button", { name: "Keep editing" }).click();
  await checkLayout(page);
  await page.setViewportSize({ width: 320, height: 800 });
  await checkLayout(page);
  await page.screenshot({ path: path.join(logDir, `${role}-drawer-320.png`) });
  await dialog.getByRole("button", { name: "Save draft" }).click();
  await dialog.getByLabel("Choose file").waitFor();
  await dialog.getByLabel("Choose file").setInputFiles({
    name: "guide.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Fictional library borrowing rules."),
  });
  await dialog.getByRole("button", { name: "Upload and index" }).click();
  await dialog.getByRole("button", { name: "Submit for review" }).click();
  await dialog
    .getByRole("button", { name: "Confirm submit for review" })
    .click();
  await dialog.getByText("Under review", { exact: true }).waitFor();
  assert.equal(
    await dialog
      .getByRole("button", { name: "Publish revision", exact: true })
      .count(),
    0,
  );
  if (role === "admin") {
    await dialog
      .getByRole("button", { name: "Approve revision", exact: true })
      .click();
    await dialog
      .getByRole("button", { name: "Confirm approve revision" })
      .click();
    await dialog
      .getByRole("button", { name: "Publish revision", exact: true })
      .click();
    await page.screenshot({
      path: path.join(logDir, "admin-publication-confirmation.png"),
    });
    await dialog
      .getByRole("button", { name: "Confirm publish revision" })
      .click();
    await dialog.getByText("Published", { exact: true }).waitFor();
    await dialog
      .getByRole("button", { name: "Unpublish resource", exact: true })
      .click();
    await dialog
      .getByRole("button", { name: "Confirm unpublish resource" })
      .click();
    await dialog.getByText("Archived", { exact: true }).waitFor();
  }
  await dialog.getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("button", { name: "Add resource" }).click();
  await page.keyboard.press("Tab");
  assert(
    await page
      .getByRole("dialog")
      .evaluate((node) => node.contains(document.activeElement)),
    "Modal contains focus",
  );
  await page.keyboard.press("Escape");
  assert(
    await page
      .getByRole("button", { name: "Add resource" })
      .evaluate((button) => button === document.activeElement),
    "Opener focus restored",
  );
}
