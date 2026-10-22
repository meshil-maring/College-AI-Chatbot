import type { AcademicEntity } from '../../../types/academicSetup.ts'

export type AcademicField = {
  key: string
  label: string
  help: string
  placeholder?: string
  type?: 'number' | 'date' | 'checkbox' | 'textarea'
  required?: boolean
  source?: AcademicEntity
  options?: string[]
  immutable?: boolean
  min?: number
}

type Definition = { label: string; id: string; help: string; example: string; requires: AcademicEntity[]; fields: AcademicField[] }

const named = (name: string, code: string): AcademicField[] => [
  { key: 'name', label: 'Name', required: true, help: `Enter the official name, for example ${name}.`, placeholder: `e.g. ${name}` },
  { key: 'code', label: 'Code', required: true, help: `Use your institution's short identifier, for example ${code}.`, placeholder: `e.g. ${code}` },
]
const description: AcademicField = { key: 'description', label: 'Description', type: 'textarea', help: 'Optional: add a short explanation for other administrators.', placeholder: 'A short description (optional)' }
const dates: AcademicField[] = [
  { key: 'start_date', label: 'Start date', type: 'date', required: true, help: 'Choose the official first day. Semester dates must fall within the academic year.' },
  { key: 'end_date', label: 'End date', type: 'date', required: true, help: 'Choose the official last day, after the start date. Semester dates must fall within the academic year.' },
  { key: 'is_current', label: 'Current', type: 'checkbox', help: 'Mark the period in use now. Only one academic year, and one semester per year, can be current. Clear Current on the previous period first.' },
]
const parent = (key: string, label: string, source: AcademicEntity, help: string, required = true): AcademicField => ({ key, label, source, help, required, immutable: true })
const capacity: AcademicField = { key: 'capacity', label: 'Capacity', type: 'number', min: 1, help: 'Optional: enter the maximum number of students, for example 60. Leave blank if no limit is specified.', placeholder: 'e.g. 60' }

export const ACADEMIC_ENTITIES: AcademicEntity[] = ['departments', 'programs', 'academic_years', 'semesters', 'courses', 'program_courses', 'course_offerings', 'sections', 'batches']
export const ACADEMIC_DEFINITIONS: Record<AcademicEntity, Definition> = {
  batches: {
    label: 'Batches', id: 'batch_id', requires: ['programs'],
    help: 'Create admission cohorts for each branch. Students choose an active batch during individual or bulk registration. A batch is separate from an academic year.',
    example: '2026–2030 for B.Tech Computer Science',
    fields: [parent('program_id', 'Branch / program', 'programs', 'Select the branch that admits this cohort. Create its degree program in College basics first.'),
      { key: 'start_year', label: 'Admission year', type: 'number', min: 1900, required: true, immutable: true, help: 'Enter the admission year, for example 2026. This is the first year of the batch.', placeholder: 'e.g. 2026' },
      { key: 'end_year', label: 'Completion year', type: 'number', min: 1901, required: true, immutable: true, help: 'Enter the expected completion year, for example 2030. It must follow the admission year by 1 to 10 years.', placeholder: 'e.g. 2030' }],
  },
  departments: {
    label: 'Departments', id: 'department_id', requires: [],
    help: 'Add the academic departments in your college. Programs and subjects will belong to these departments.',
    example: 'Computer Science (CSE)', fields: [...named('Computer Science', 'CSE'), description],
  },
  programs: {
    label: 'Programs', id: 'program_id', requires: ['departments'],
    help: 'Add the degrees offered by each department, including their duration.', example: 'B.Tech Computer Science in the CSE department',
    fields: [parent('department_id', 'Department', 'departments', 'Select the department that offers this degree. Add its department in College basics first.'), ...named('B.Tech Computer Science', 'BTECH-CSE'),
      { key: 'degree_type', label: 'Degree type', required: true, help: 'Enter the qualification awarded, such as B.Tech, B.Sc, B.Com or MBA.', placeholder: 'e.g. B.Tech' },
      { key: 'duration_years', label: 'Duration in years', type: 'number', min: 0.01, required: true, help: 'Enter the normal length of the degree in years, for example 4 for a four-year program.', placeholder: 'e.g. 4' },
      { key: 'total_credits', label: 'Total credits', type: 'number', min: 0.01, help: 'Optional: enter the credits needed to complete this degree, as stated in your curriculum.', placeholder: 'e.g. 160' }, description],
  },
  academic_years: {
    label: 'Academic Years', id: 'academic_year_id', requires: [],
    help: 'Set the start and end dates of each academic year. Active academic years cannot overlap.', example: '2026–2027, from 1 July 2026 to 30 June 2027',
    fields: [...named('2026–2027', 'AY2026'), ...dates],
  },
  semesters: {
    label: 'Semesters', id: 'semester_id', requires: ['academic_years'],
    help: 'Add teaching terms within an academic year. These terms are shared across programs; their dates must fit inside the year.', example: 'Semester 1 in academic year 2026–2027',
    fields: [parent('academic_year_id', 'Academic year', 'academic_years', 'Select the year containing this term. Add the academic year in Calendar first.'), ...named('Semester 1', 'SEM1'),
      { key: 'semester_number', label: 'Semester number', type: 'number', min: 1, required: true, help: 'Enter the term number, for example 1 or 2. The number and code must be unique within this academic year.', placeholder: 'e.g. 1' }, ...dates],
  },
  courses: {
    label: 'Courses / Subjects', id: 'course_id', requires: ['departments'],
    help: 'Add each subject once. Connect it to a named curriculum and classify it in Curricula & packages.', example: 'Programming Fundamentals (CS101)',
    fields: [parent('department_id', 'Department', 'departments', 'Select the department responsible for this subject. It can later be used by programs in other departments.'), ...named('Programming Fundamentals', 'CS101'),
      { key: 'credits', label: 'Credits', type: 'number', min: 0.01, help: 'Optional: enter this subject\'s credit value from the approved syllabus, for example 3.', placeholder: 'e.g. 3' },
      ...['lecture', 'tutorial', 'practical'].map((kind): AcademicField => ({ key: `${kind}_hours`, label: `${kind[0].toUpperCase()}${kind.slice(1)} hours`, type: 'number', min: 0, help: `Optional: enter the ${kind} hours listed in your approved syllabus. Use 0 if there are none.`, placeholder: 'e.g. 0' })), description],
  },
  program_courses: {
    label: 'Program Curriculum', id: 'program_course_id', requires: ['programs', 'courses'],
    help: 'Manage reusable or dated subject links for each degree. Named curricula and their packages are managed in Curricula & packages.', example: 'CS101 as a required core subject in B.Tech Computer Science',
    fields: [parent('program_id', 'Program', 'programs', 'Select the degree whose curriculum you are building. Create it in Step 2 first.'),
      parent('course_id', 'Course / subject', 'courses', 'Select a subject created in Step 5. Subjects from any department in your college are allowed.'),
      parent('semester_id', 'Semester (optional)', 'semesters', 'Leave Any semester for a reusable curriculum link. Selecting a semester limits this link to that exact term and academic year.', false),
      { key: 'course_type', label: 'Course type', required: true, options: ['core', 'elective', 'open_elective', 'skill', 'project'], help: 'Core: a main subject. Elective: a choice within the program. Open elective: a broader choice. Skill: practical training. Project: project work.' },
      { key: 'is_required', label: 'Required subject', type: 'checkbox', help: 'Check this if every student in the program must complete the subject. Leave unchecked for an optional subject.' }],
  },
  course_offerings: {
    label: 'Course Offerings', id: 'course_offering_id', requires: ['programs', 'academic_years', 'semesters', 'courses', 'program_courses'],
    help: 'Schedule a subject for a degree in a specific year and semester. A matching named curriculum class or a Program Curriculum link makes the subject available.', example: 'CS101 for B.Tech Computer Science, 2026–2027, Semester 1',
    fields: [parent('program_id', 'Program', 'programs', 'Select the degree that will study this subject.'),
      parent('academic_year_id', 'Academic year', 'academic_years', 'Select the year in which the subject will be taught.'),
      parent('semester_id', 'Semester', 'semesters', 'Select the academic year first. Only its active semesters are listed.'),
      parent('course_id', 'Course / subject', 'courses', 'Select the program, year and semester first. Subjects from a matching named curriculum class or an applicable Program Curriculum link are listed.'), capacity],
  },
  sections: {
    label: 'Sections', id: 'section_id', requires: ['course_offerings'],
    help: 'Divide an offered subject into teaching groups. Create a section for each subject taught to that class.', example: 'Section A for the CS101 offering, with capacity 60',
    fields: [parent('course_offering_id', 'Course offering', 'course_offerings', 'Select the subject, degree, year and semester combination created in Step 7.'),
      { key: 'name', label: 'Name', required: true, help: 'Enter the teaching group name, for example Section A.', placeholder: 'e.g. Section A' },
      { key: 'code', label: 'Section code', required: true, immutable: true, help: 'Use the same code, for example A, for sibling subjects taught to the same class. This code cannot be changed after saving.', placeholder: 'e.g. A' }, capacity],
  },
}
