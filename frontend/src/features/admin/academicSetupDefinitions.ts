import type { AcademicEntity } from '../../types/academicSetup.ts'

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

export const ACADEMIC_ENTITIES: AcademicEntity[] = ['departments', 'programs', 'academic_years', 'semesters', 'courses', 'program_courses', 'course_offerings', 'sections']
export const ACADEMIC_DEFINITIONS: Record<AcademicEntity, Definition> = {
  departments: {
    label: 'Departments', id: 'department_id', requires: [],
    help: 'Add the academic departments in your college. Programs and subjects will belong to these departments.',
    example: 'Computer Science (CSE)', fields: [...named('Computer Science', 'CSE'), description],
  },
  programs: {
    label: 'Programs', id: 'program_id', requires: ['departments'],
    help: 'Add the degrees offered by each department, including their duration.', example: 'B.Tech Computer Science in the CSE department',
    fields: [parent('department_id', 'Department', 'departments', 'Select the department that offers this degree. Add the department in Step 1 first.'), ...named('B.Tech Computer Science', 'BTECH-CSE'),
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
    fields: [parent('academic_year_id', 'Academic year', 'academic_years', 'Select the year containing this term. Add the academic year in Step 3 first.'), ...named('Semester 1', 'SEM1'),
      { key: 'semester_number', label: 'Semester number', type: 'number', min: 1, required: true, help: 'Enter the term number, for example 1 or 2. The number and code must be unique within this academic year.', placeholder: 'e.g. 1' }, ...dates],
  },
  courses: {
    label: 'Courses / Subjects', id: 'course_id', requires: ['departments'],
    help: 'Add each subject once. You will connect it to degrees in the next step.', example: 'Programming Fundamentals (CS101)',
    fields: [parent('department_id', 'Department', 'departments', 'Select the department responsible for this subject. It can later be used by programs in other departments.'), ...named('Programming Fundamentals', 'CS101'),
      { key: 'credits', label: 'Credits', type: 'number', min: 0.01, help: 'Optional: enter this subject\'s credit value from the approved syllabus, for example 3.', placeholder: 'e.g. 3' },
      ...['lecture', 'tutorial', 'practical'].map((kind): AcademicField => ({ key: `${kind}_hours`, label: `${kind[0].toUpperCase()}${kind.slice(1)} hours`, type: 'number', min: 0, help: `Optional: enter the ${kind} hours listed in your approved syllabus. Use 0 if there are none.`, placeholder: 'e.g. 0' })), description],
  },
  program_courses: {
    label: 'Program Curriculum', id: 'program_course_id', requires: ['programs', 'courses'],
    help: 'Choose which subjects belong to each degree and whether they are core or elective.', example: 'CS101 as a required core subject in B.Tech Computer Science',
    fields: [parent('program_id', 'Program', 'programs', 'Select the degree whose curriculum you are building. Create it in Step 2 first.'),
      parent('course_id', 'Course / subject', 'courses', 'Select a subject created in Step 5. Subjects from any department in your college are allowed.'),
      parent('semester_id', 'Semester (optional)', 'semesters', 'Leave Any semester for a reusable curriculum link. Selecting a semester limits this link to that exact term and academic year.', false),
      { key: 'course_type', label: 'Course type', required: true, options: ['core', 'elective', 'open_elective', 'skill', 'project'], help: 'Core: a main subject. Elective: a choice within the program. Open elective: a broader choice. Skill: practical training. Project: project work.' },
      { key: 'is_required', label: 'Required subject', type: 'checkbox', help: 'Check this if every student in the program must complete the subject. Leave unchecked for an optional subject.' }],
  },
  course_offerings: {
    label: 'Course Offerings', id: 'course_offering_id', requires: ['programs', 'academic_years', 'semesters', 'courses', 'program_courses'],
    help: 'Schedule a curriculum subject for a degree in a specific year and semester.', example: 'CS101 for B.Tech Computer Science, 2026–2027, Semester 1',
    fields: [parent('program_id', 'Program', 'programs', 'Select the degree that will study this subject.'),
      parent('academic_year_id', 'Academic year', 'academic_years', 'Select the year in which the subject will be taught.'),
      parent('semester_id', 'Semester', 'semesters', 'Select the academic year first. Only its active semesters are listed.'),
      parent('course_id', 'Course / subject', 'courses', 'Select the program, year and semester first. Only subjects linked to that program and semester in Step 6 are listed.'), capacity],
  },
  sections: {
    label: 'Sections', id: 'section_id', requires: ['course_offerings'],
    help: 'Divide an offered subject into teaching groups. Create a section for each subject taught to that class.', example: 'Section A for the CS101 offering, with capacity 60',
    fields: [parent('course_offering_id', 'Course offering', 'course_offerings', 'Select the subject, degree, year and semester combination created in Step 7.'),
      { key: 'name', label: 'Name', required: true, help: 'Enter the teaching group name, for example Section A.', placeholder: 'e.g. Section A' },
      { key: 'code', label: 'Section code', required: true, immutable: true, help: 'Use the same code, for example A, for sibling subjects taught to the same class. This code cannot be changed after saving.', placeholder: 'e.g. A' }, capacity],
  },
}
