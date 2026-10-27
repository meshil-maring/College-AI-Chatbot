import { catalogue, program, structureCatalogue, year } from './AcademicSetup.support.ts'
import { course, semester, populateExportCatalogue } from './academicExportFixtures.ts'
import type { StructureRecordMap } from '../../../../types/academicStructure.ts'

const context = {
  institution_id: 'institution-1',
  is_active: true,
  created_at: '2026-10-27T00:00:00Z',
  updated_at: '2026-10-27T00:00:00Z',
}
export const stage: StructureRecordMap['program_semesters'] = {
  ...context,
  program_semester_id: 'stage-1',
  program_id: program.program_id,
  name: 'Semester 1',
  code: 'S1',
  semester_number: 1,
}
export const version: StructureRecordMap['curriculum_versions'] = {
  ...context,
  curriculum_version_id: 'version-1',
  program_id: program.program_id,
  academic_year_id: year.academic_year_id,
  name: 'CSE Curriculum',
  version: '1.0',
  total_semesters: 8,
  description: null,
  status: 'published',
  published_at: context.created_at,
}
export const mapping: StructureRecordMap['curriculum_subjects'] = {
  ...context,
  curriculum_subject_id: 'mapping-1',
  curriculum_version_id: version.curriculum_version_id,
  program_semester_id: stage.program_semester_id,
  course_id: course.course_id,
  course_type: 'core',
  is_required: true,
}
export const cohort: StructureRecordMap['admission_cohorts'] = {
  ...context,
  admission_cohort_id: 'cohort-1',
  program_id: program.program_id,
  academic_year_id: year.academic_year_id,
  curriculum_version_id: version.curriculum_version_id,
  name: 'CSE 2026',
  code: 'CSE26',
  start_year: 2026,
  end_year: 2030,
  expected_count: 120,
  description: null,
  status: 'active',
}
export const section: StructureRecordMap['academic_sections'] = {
  ...context,
  academic_section_id: 'section-1',
  admission_cohort_id: cohort.admission_cohort_id,
  program_semester_id: stage.program_semester_id,
  semester_id: semester.semester_id,
  name: 'Section A',
  code: 'CSE26A',
  capacity: 60,
  description: null,
}
export const offering: StructureRecordMap['academic_offerings'] = {
  ...context,
  academic_offering_id: 'offering-1',
  academic_section_id: section.academic_section_id,
  curriculum_subject_id: mapping.curriculum_subject_id,
  capacity: 60,
}
export function populateStructure() {
  populateExportCatalogue()
  catalogue.records.academic_years = [structuredClone(year)]
  structureCatalogue.records = {
    program_semesters: [structuredClone(stage)],
    curriculum_versions: [structuredClone(version)],
    curriculum_subjects: [structuredClone(mapping)],
    admission_cohorts: [structuredClone(cohort)],
    academic_sections: [structuredClone(section)],
    academic_offerings: [structuredClone(offering)],
  }
}
