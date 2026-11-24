import type { AcademicCatalogue } from '../../../../../types/academicSetup.ts'
import type { StructureCatalogue } from '../../../../../types/academicStructure.ts'

const base = { institution_id: 'i1', is_active: true, created_at: '', updated_at: '' }

/**
 * 2026–27 with an Odd and an Even term. CSE 2026 (4-year B.Tech, 8 semesters)
 * has Sections A and B in Semester 1 and Section A in Semester 2. CSE 2023 is
 * in its final semesters and must not continue.
 */
export function scenario() {
  const catalogue = {
    institution_id: 'i1',
    manageable: ['academic_years', 'semesters', 'courses'],
    records: {
      academic_years: [
        {
          ...base,
          academic_year_id: 'y26',
          name: '2026 - 2027',
          code: 'AY2026',
          start_date: '2026-08-01',
          end_date: '2027-07-31',
          is_current: true,
        },
      ],
      semesters: [
        {
          ...base,
          semester_id: 'odd26',
          academic_year_id: 'y26',
          name: 'Odd Term 2026',
          code: 'ODD26',
          semester_number: 1,
          start_date: '2026-08-01',
          end_date: '2027-01-29',
          is_current: false,
        },
        {
          ...base,
          semester_id: 'even27',
          academic_year_id: 'y26',
          name: 'Even Term 2027',
          code: 'EVEN27',
          semester_number: 2,
          start_date: '2027-01-30',
          end_date: '2027-07-31',
          is_current: false,
        },
      ],
    },
  } as unknown as AcademicCatalogue
  const stage = (n: number, program = 'p1') => ({
    ...base,
    program_semester_id: `${program}-s${n}`,
    program_id: program,
    name: `Semester ${n}`,
    code: `SEM-${n}`,
    semester_number: n,
  })
  const section = (id: string, batch: string, stageId: string, term: string, name: string, code: string) => ({
    ...base,
    academic_section_id: id,
    admission_cohort_id: batch,
    program_semester_id: stageId,
    semester_id: term,
    name,
    code,
    capacity: 60,
    description: null,
  })
  const structure = {
    institution_id: 'i1',
    manageable: ['program_semesters', 'academic_sections', 'academic_offerings'],
    activities: [],
    records: {
      program_semesters: [stage(1), stage(2), stage(3), stage(7), stage(8)],
      curriculum_versions: [
        {
          ...base,
          curriculum_version_id: 'v1',
          program_id: 'p1',
          academic_year_id: 'y26',
          name: 'BT',
          version: '1.0',
          total_semesters: 8,
          description: null,
          status: 'published',
          published_at: '',
        },
      ],
      curriculum_subjects: [
        {
          ...base,
          curriculum_subject_id: 'm3a',
          curriculum_version_id: 'v1',
          program_semester_id: 'p1-s3',
          course_id: 'c1',
          course_type: 'core',
          is_required: true,
        },
        {
          ...base,
          curriculum_subject_id: 'm3b',
          curriculum_version_id: 'v1',
          program_semester_id: 'p1-s3',
          course_id: 'c2',
          course_type: 'elective',
          is_required: false,
        },
        {
          ...base,
          curriculum_subject_id: 'm3x',
          curriculum_version_id: 'v1',
          program_semester_id: 'p1-s3',
          course_id: 'c3',
          course_type: 'core',
          is_required: true,
          is_active: false,
        },
      ],
      admission_cohorts: [
        {
          ...base,
          admission_cohort_id: 'b26',
          program_id: 'p1',
          curriculum_version_id: 'v1',
          academic_year_id: 'y26',
          name: 'CSE 2026',
          code: 'CSE26',
          start_year: 2026,
          end_year: 2030,
          expected_count: null,
          description: null,
          status: 'active',
        },
        {
          ...base,
          admission_cohort_id: 'b23',
          program_id: 'p1',
          curriculum_version_id: 'v1',
          academic_year_id: 'y26',
          name: 'CSE 2023',
          code: 'CSE23',
          start_year: 2023,
          end_year: 2027,
          expected_count: null,
          description: null,
          status: 'active',
        },
      ],
      academic_sections: [
        section('a1', 'b26', 'p1-s1', 'odd26', 'Section A (Semester 1)', 'A'),
        section('b1', 'b26', 'p1-s1', 'odd26', 'Section B', 'B'),
        section('a2', 'b26', 'p1-s2', 'even27', 'Section A (Semester 2)', 'A'),
        section('f7', 'b23', 'p1-s7', 'odd26', 'Section A', 'A'),
      ],
      academic_offerings: [],
    },
  } as unknown as StructureCatalogue
  return { catalogue, structure }
}
