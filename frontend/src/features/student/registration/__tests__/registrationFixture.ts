import type { StudentSemester } from '../../../../types/semesterRegistration.ts'

const names = [
  'Data Structures and Algorithms',
  'OOP',
  'Digital Logic Design',
  'Discrete Mathematics',
  'Computer Organization and Architecture',
  'DBMS',
  'Data Structures / OOP Laboratory',
  'Digital Logic Design Laboratory',
]

export function semesterFixture(): StudentSemester {
  return {
    semester_registration_id: 'registration-1',
    institution_id: 'tenant-1',
    student_id: 'student-1',
    academic_section_id: 'section-1',
    semester_id: 'term-1',
    status: 'assigned',
    selected_option_ids: [],
    assigned_at: '2026-10-29',
    registered_at: null,
    section_name: 'Section A',
    batch_name: 'CSE 2025–2029',
    program_name: 'B.Tech CSE',
    program_semester_name: 'Semester 3',
    term_name: 'July–December 2026',
    start_date: '2026-07-01',
    end_date: '2026-12-31',
    enrolled_subjects: [],
    groups: [
      {
        choice_group_id: 'group-1',
        institution_id: 'tenant-1',
        curriculum_version_id: 'version-1',
        program_semester_id: 'stage-3',
        name: 'Semester 3 choices',
        options: [
          {
            choice_option_id: 'option-1',
            name: 'Option 1',
            curriculum_subject_ids: ['subject-3', 'subject-4', 'subject-5'],
          },
          {
            choice_option_id: 'option-2',
            name: 'Option 2',
            curriculum_subject_ids: ['subject-6', 'subject-7', 'subject-8'],
          },
        ],
      },
    ],
    subjects: names.map((name, index) => ({
      curriculum_subject_id: `subject-${index + 1}`,
      name,
      code: `CS${index + 1}`,
      credits: 3,
      is_required: index < 2,
      academic_offering_id: `offering-${index + 1}`,
      available: true,
    })),
  }
}
