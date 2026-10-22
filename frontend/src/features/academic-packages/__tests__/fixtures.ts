import type { AcademicPackageCatalogue } from '../../../types/academicPackages.ts'

export function catalogue(): AcademicPackageCatalogue {
  return {
    institution_id: 'institution',
    capabilities: ['select', 'request'],
    options: {
      programs: [{ program_id: 'program', name: 'B.Tech Computer Science', code: 'CSE' }],
      batches: [{ batch_id: 'batch', program_id: 'program', start_year: 2026, end_year: 2030 }],
      semesters: [{ semester_id: 'term', name: 'Autumn 2026' }],
      registrations: [
        {
          registration_id: 'registration',
          student_name: 'Ada Rao',
          register_number: 'CS001',
          program_id: 'program',
          batch_id: 'batch',
        },
      ],
      subjects: [
        { course_id: 'dsa', name: 'Data Structures', code: 'DSA' },
        { course_id: 'ml', name: 'Machine Learning', code: 'ML' },
        { course_id: 'a', name: 'Subject A', code: 'A' },
        { course_id: 'e', name: 'Subject E', code: 'E' },
      ],
      sections: [],
      responsibilities: [],
    },
    records: {
      curricula: [
        { curriculum_id: 'curriculum', program_id: 'program', name: 'CSE 2026', code: 'CSE2026', version: 1 },
      ],
      curriculum_subjects: [
        {
          curriculum_subject_id: 'cs-dsa',
          curriculum_id: 'curriculum',
          course_id: 'dsa',
          study_semester: 1,
          course_type: 'core',
          is_core: true,
        },
        {
          curriculum_subject_id: 'cs-ml',
          curriculum_id: 'curriculum',
          course_id: 'ml',
          study_semester: 1,
          course_type: 'core',
          is_core: true,
        },
        {
          curriculum_subject_id: 'cs-a',
          curriculum_id: 'curriculum',
          course_id: 'a',
          study_semester: 1,
          course_type: 'elective',
          is_core: false,
        },
        {
          curriculum_subject_id: 'cs-e',
          curriculum_id: 'curriculum',
          course_id: 'e',
          study_semester: 1,
          course_type: 'open_elective',
          is_core: false,
        },
      ],
      packages: [
        { package_id: 'abc', curriculum_id: 'curriculum', study_semester: 1, name: 'Package ABC', code: 'ABC' },
        { package_id: 'efg', curriculum_id: 'curriculum', study_semester: 1, name: 'Package EFG', code: 'EFG' },
      ],
      package_subjects: [
        { package_subject_id: 'ps-a', package_id: 'abc', curriculum_subject_id: 'cs-a' },
        { package_subject_id: 'ps-e', package_id: 'efg', curriculum_subject_id: 'cs-e' },
      ],
      classes: [
        {
          class_id: 'class',
          program_id: 'program',
          batch_id: 'batch',
          semester_id: 'term',
          study_semester: 1,
          section_code: 'A',
          code: 'CSE-2026-A',
          curriculum_id: 'curriculum',
          student_choice_enabled: true,
          change_cutoff: '2099-10-01T00:00:00Z',
        },
      ],
      class_packages: [
        {
          class_package_id: 'cp-a',
          class_id: 'class',
          package_id: 'abc',
          enabled: true,
          selection_code: 'CSE202-ABCD',
        },
        {
          class_package_id: 'cp-e',
          class_id: 'class',
          package_id: 'efg',
          enabled: true,
          selection_code: 'CSE202-DEEBS',
        },
      ],
      placements: [{ placement_id: 'placement', class_id: 'class', registration_id: 'registration' }],
      assignments: [],
      requests: [],
      history: [],
      class_subjects: [],
      class_responsibilities: [],
    },
  }
}

export function assignedCatalogue() {
  const data = catalogue()
  data.records.assignments = [
    { assignment_id: 'assignment', placement_id: 'placement', package_id: 'abc', revision: 3 },
  ]
  return data
}
