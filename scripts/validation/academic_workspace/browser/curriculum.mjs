import {
  field,
  navigate,
  open,
  remember,
  save,
  structure,
} from "./helpers.mjs";

export async function createCurriculum(page, settings, records) {
  const prefix = settings.prefix;
  let dialog;
  if (!records.program_semesters) {
    await navigate(page, "Program Semesters");
    dialog = await open(page, "Program Semester");
    await field(dialog, "Program").selectOption(records.programs.program_id);
    await field(dialog, "Semester Name").fill(`${prefix} Stage One`);
    await field(dialog, "Semester Code").fill("S1");
    await field(dialog, "Semester Number").fill("1");
    await remember(
      settings,
      records,
      "program_semesters",
      await save(
        page,
        dialog,
        `${structure}/program_semesters`,
        "Create Program Semester",
      ),
    );
  }
  await navigate(page, "Curriculum Versions");
  if (!records.curriculum_versions) {
    dialog = await open(page, "Curriculum");
    await field(dialog, "Program").selectOption(records.programs.program_id);
    await field(dialog, "Academic Year").selectOption(
      records.academic_years.academic_year_id,
    );
    await field(dialog, "Curriculum Name").fill(`${prefix} Curriculum`);
    await field(dialog, "Version").fill("1.0");
    await field(dialog, "Total Semesters").fill("2");
    await remember(
      settings,
      records,
      "curriculum_versions",
      await save(
        page,
        dialog,
        `${structure}/curriculum_versions`,
        "Create Curriculum",
      ),
    );
  }
  if (!records.curriculum_subjects) {
    await page
      .getByRole("tab", { name: "Subject Mapping", exact: true })
      .click();
    dialog = await open(page, "Subject Mapping");
    await field(dialog, "Curriculum Version").selectOption(
      records.curriculum_versions.curriculum_version_id,
    );
    await field(dialog, "Program Semester").selectOption(
      records.program_semesters.program_semester_id,
    );
    await field(dialog, "Subject").selectOption(records.courses.course_id);
    await remember(
      settings,
      records,
      "curriculum_subjects",
      await save(
        page,
        dialog,
        `${structure}/curriculum_subjects`,
        "Create Subject Mapping",
      ),
    );
  }
  if (records.curriculum_versions.status === "published") return;
  await page.getByRole("tab", { name: "Curriculum List", exact: true }).click();
  await page
    .getByRole("searchbox", { name: "Search academic records", exact: true })
    .fill(prefix);
  await page
    .getByRole("button", { name: `Edit ${prefix} Curriculum`, exact: true })
    .click();
  dialog = page.getByRole("dialog", { name: "Edit Curriculum", exact: true });
  await field(dialog, "Publication Status").selectOption("published");
  await dialog
    .getByRole("button", { name: "Save Changes", exact: true })
    .click();
  const confirmation = page.getByRole("alertdialog", {
    name: "Confirm status change",
    exact: true,
  });
  await remember(
    settings,
    records,
    "curriculum_versions",
    await save(
      page,
      confirmation,
      `${structure}/curriculum_versions/${records.curriculum_versions.curriculum_version_id}`,
      "Confirm Change",
      "PATCH",
    ),
  );
}
