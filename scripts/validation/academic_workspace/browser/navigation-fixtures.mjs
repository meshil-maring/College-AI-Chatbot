// Local browser fixtures: this journey never contacts a backend or signs in.
const institution_id = "institution-1";
const row = (values) => ({ institution_id, is_active: true, ...values });

export const user = {
  authenticated: true,
  user_id: "admin-1",
  auth_user_id: "auth-1",
  email: "admin@example.invalid",
  role: "admin",
  institution_id,
  institution_code: "TEST",
  effective_permissions: ["*"],
};

export const catalogue = {
  institution_id,
  records: {
    departments: [
      row({
        department_id: "department-1",
        name: "Computer Science and Engineering",
        code: "CSE",
      }),
    ],
    programs: [
      row({
        program_id: "program-1",
        department_id: "department-1",
        name: "B.Tech CSE",
        code: "BTECH-CSE",
        degree_type: "B.Tech",
        duration_years: 4,
        total_credits: 160,
      }),
    ],
    academic_years: [
      row({
        academic_year_id: "year-1",
        name: "2026–2027",
        code: "2026-27",
        start_date: "2026-07-01",
        end_date: "2027-06-30",
        is_current: true,
      }),
    ],
    semesters: [
      row({
        semester_id: "term-1",
        academic_year_id: "year-1",
        name: "Autumn 2026",
        code: "AUT26",
        semester_number: 1,
        start_date: "2026-07-01",
        end_date: "2026-12-31",
        is_current: true,
      }),
    ],
    courses: ["Digital Logic Design", "Database Management Systems (DBMS)"].map(
      (name, index) =>
        row({
          course_id: `course-${index}`,
          department_id: "department-1",
          name,
          code: `CS${index}`,
          credits: 3,
        }),
    ),
    program_courses: [],
    course_offerings: [],
    sections: [],
  },
  manageable: [
    "departments",
    "programs",
    "academic_years",
    "semesters",
    "courses",
  ],
};

export const structure = {
  institution_id,
  records: {
    program_semesters: [
      row({
        program_semester_id: "stage-1",
        program_id: "program-1",
        name: "Semester 3",
        code: "S3",
        semester_number: 3,
      }),
    ],
    curriculum_versions: [
      row({
        curriculum_version_id: "version-1",
        program_id: "program-1",
        academic_year_id: "year-1",
        name: "CSE S-3 2026",
        version: "1.0",
        total_semesters: 8,
        status: "draft",
        published_at: null,
      }),
    ],
    curriculum_subjects: [0, 1].map((index) =>
      row({
        curriculum_subject_id: `mapping-${index}`,
        curriculum_version_id: "version-1",
        program_semester_id: "stage-1",
        course_id: `course-${index}`,
        course_type: "elective",
        is_required: false,
      }),
    ),
    admission_cohorts: [
      row({
        admission_cohort_id: "batch-1",
        program_id: "program-1",
        academic_year_id: "year-1",
        curriculum_version_id: "version-1",
        name: "CSE 2026",
        code: "CSE26",
        start_year: 2026,
        end_year: 2030,
        expected_count: 60,
        status: "active",
      }),
    ],
    academic_sections: [
      row({
        academic_section_id: "section-1",
        admission_cohort_id: "batch-1",
        program_semester_id: "stage-1",
        semester_id: "term-1",
        name: "Section A",
        code: "CSE26A",
        capacity: 60,
      }),
    ],
    academic_offerings: [],
  },
  manageable: [
    "program_semesters",
    "curriculum_versions",
    "curriculum_subjects",
    "admission_cohorts",
    "academic_sections",
    "academic_offerings",
  ],
  activities: [],
};

export const registration = {
  institution_id,
  can_assign: true,
  can_manage_choices: true,
  students: [],
  assignments: [],
  groups: [
    {
      choice_group_id: "group-1",
      institution_id,
      curriculum_version_id: "version-1",
      program_semester_id: "stage-1",
      name: "Semester 3 subject choices",
      options: [0, 1].map((index) => ({
        choice_option_id: `option-${index}`,
        name: `Option ${index + 1}`,
        curriculum_subject_ids: [`mapping-${index}`],
      })),
    },
  ],
};
