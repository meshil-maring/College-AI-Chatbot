import assert from "node:assert/strict";
import {
  field,
  api,
  base,
  navigate,
  open,
  remember,
  save,
} from "./helpers.mjs";

export async function createCatalogue(page, settings, records) {
  const prefix = settings.prefix;
  await navigate(page, "Departments");
  let dialog = await open(page, "Department");
  await dialog
    .getByRole("textbox", { name: "Department Name", exact: true })
    .fill(`${prefix} Reliability`);
  await dialog
    .getByRole("textbox", { name: "Department Code", exact: true })
    .fill(`${prefix}D`);
  await dialog.getByRole("radio", { name: /^Active/ }).check();
  const endpoint = `${base}/departments`;
  await page.route(`**${endpoint}`, (route) =>
    route.request().method() === "POST"
      ? route.abort("failed")
      : route.continue(),
  );
  await dialog
    .getByRole("button", { name: "Create Department", exact: true })
    .click();
  await dialog.getByRole("alert").waitFor();
  assert.equal(
    await dialog
      .getByRole("textbox", { name: "Department Name", exact: true })
      .inputValue(),
    `${prefix} Reliability`,
  );
  await page.unroute(`**${endpoint}`);
  console.log("PASS: failed save retains entries and permits retry");
  const department = await save(page, dialog, endpoint, "Create Department");
  await remember(settings, records, "departments", department);
  const catalogue = await api(page, base);
  assert.equal(
    catalogue.records.departments.filter((row) => row.code === `${prefix}D`)
      .length,
    1,
  );
  console.log("PASS: retry created exactly one department");

  await navigate(page, "Programs");
  dialog = await open(page, "Program");
  await dialog
    .getByRole("textbox", { name: "Program Name", exact: true })
    .fill(`${prefix} Applied Science`);
  await dialog
    .getByRole("textbox", { name: "Program Code", exact: true })
    .fill(`${prefix}P`);
  await dialog
    .getByRole("combobox", { name: "Department", exact: true })
    .selectOption(department.department_id);
  await dialog
    .getByRole("combobox", { name: "Degree Type", exact: true })
    .selectOption("B.Sc");
  await field(dialog, "Duration (Years)").fill("1");
  await field(dialog, "Total Credits (Optional)").fill("4");
  await dialog.getByRole("radio", { name: /^Active/ }).check();
  await remember(
    settings,
    records,
    "programs",
    await save(page, dialog, `${base}/programs`, "Create Program"),
  );

  await navigate(page, "Academic Years");
  dialog = await open(page, "Academic Year");
  const years = catalogue.records.academic_years.map((row) =>
    Number(row.start_date.slice(0, 4)),
  );
  const start = Math.max(2035, ...years.map((year) => year + 1));
  await field(dialog, "Academic Year Name").fill(
    `${prefix} ${start}-${start + 1}`,
  );
  await field(dialog, "Academic Year Code").fill(`${prefix}Y`);
  await dialog.locator("#calendar-start").fill(`${start}-08-01`);
  await dialog.locator("#calendar-end").fill(`${start + 1}-07-31`);
  await remember(
    settings,
    records,
    "academic_years",
    await save(page, dialog, `${base}/academic_years`, "Create Academic Year"),
  );
  const updated = await api(page, base);
  const terms = updated.records.semesters.filter(
    (row) => row.academic_year_id === records.academic_years.academic_year_id,
  );
  assert.equal(terms.length, 2);
  await remember(settings, records, "semesters", terms);

  await navigate(page, "Subjects");
  dialog = await open(page, "Subject");
  await field(dialog, "Subject Name").fill(`${prefix} Reliable Systems`);
  await field(dialog, "Subject Code").fill(`${prefix}C`);
  await dialog
    .getByRole("combobox", { name: "Department", exact: true })
    .selectOption(department.department_id);
  await field(dialog, "Credits (Optional)").fill("4");
  await dialog.getByRole("radio", { name: /^Active/ }).check();
  await remember(
    settings,
    records,
    "courses",
    await save(page, dialog, `${base}/courses`, "Create Subject"),
  );
}
