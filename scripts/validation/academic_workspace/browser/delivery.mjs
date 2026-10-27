import assert from "node:assert/strict";
import {
  field,
  api,
  base,
  navigate,
  open,
  remember,
  save,
  structure,
} from "./helpers.mjs";

export async function createDelivery(page, settings, records) {
  const prefix = settings.prefix;
  await navigate(page, "Batches");
  let dialog = await open(page, "Batch");
  await field(dialog, "Batch Name").fill(`${prefix} Batch`);
  await field(dialog, "Batch Code").fill(`${prefix}B`);
  await field(dialog, "Program").selectOption(records.programs.program_id);
  await field(dialog, "Curriculum Version").selectOption(
    records.curriculum_versions.curriculum_version_id,
  );
  await field(dialog, "Academic Year").selectOption(
    records.academic_years.academic_year_id,
  );
  const start = Number(records.academic_years.start_date.slice(0, 4));
  await field(dialog, "Start Year").fill(String(start));
  await field(dialog, "End Year").fill(String(start + 1));
  await field(dialog, "Expected Student Count (Optional)").fill("20");
  await dialog.getByRole("radio", { name: /^Active/ }).check();
  await remember(
    settings,
    records,
    "admission_cohorts",
    await save(page, dialog, `${structure}/admission_cohorts`, "Create Batch"),
  );

  await navigate(page, "Academic Sections");
  dialog = await open(page, "Section");
  await field(dialog, "Section Name").fill(`${prefix} Section A`);
  await field(dialog, "Section Code").fill(`${prefix}A`);
  await field(dialog, "Batch").selectOption(
    records.admission_cohorts.admission_cohort_id,
  );
  await field(dialog, "Program Semester").selectOption(
    records.program_semesters.program_semester_id,
  );
  await field(dialog, "Teaching Term").selectOption(
    records.semesters[0].semester_id,
  );
  await field(dialog, "Maximum Capacity (Optional)").fill("20");
  await dialog.getByRole("radio", { name: /^Active/ }).check();
  await remember(
    settings,
    records,
    "academic_sections",
    await save(
      page,
      dialog,
      `${structure}/academic_sections`,
      "Create Section",
    ),
  );

  await navigate(page, "Academic Offerings");
  dialog = await open(page, "Academic Offering");
  await field(dialog, "Section").selectOption(
    records.academic_sections.academic_section_id,
  );
  await field(dialog, "Curriculum Subject").selectOption(
    records.curriculum_subjects.curriculum_subject_id,
  );
  await field(dialog, "Maximum Capacity").fill("20");
  await remember(
    settings,
    records,
    "academic_offerings",
    await save(
      page,
      dialog,
      `${structure}/academic_offerings`,
      "Create Academic Offering",
    ),
  );

  const catalogue = await api(page, base);
  const graph = await api(page, structure);
  const offering = graph.records.academic_offerings.find(
    (row) =>
      row.academic_offering_id ===
      records.academic_offerings.academic_offering_id,
  );
  assert.equal(
    offering.academic_section_id,
    records.academic_sections.academic_section_id,
  );
  assert.equal(
    offering.curriculum_subject_id,
    records.curriculum_subjects.curriculum_subject_id,
  );
  assert.equal(offering.capacity, 20);
  assert.equal(
    graph.records.curriculum_versions.find(
      (row) =>
        row.curriculum_version_id ===
        records.curriculum_versions.curriculum_version_id,
    ).status,
    "published",
  );
  assert.equal(
    catalogue.records.programs.find(
      (row) => row.program_id === records.programs.program_id,
    ).total_credits,
    4,
  );
  console.log(
    "PASS: saved offering ancestry, publication, credits and capacity verified through real authenticated APIs",
  );
}
