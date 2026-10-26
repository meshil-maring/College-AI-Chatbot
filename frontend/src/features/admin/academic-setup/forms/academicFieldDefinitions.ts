import type { AcademicEntity } from '../../../../types/academicSetup.ts'
import type { AcademicTextField } from '../academicSetupForm.ts'

export interface AcademicField {
  key: AcademicTextField
  label: string
  type?: 'text' | 'date' | 'number'
  required?: boolean
  min?: number
  step?: string
}
const dates: AcademicField[] = [
  { key: 'start_date', label: 'Start date', type: 'date', required: true },
  { key: 'end_date', label: 'End date', type: 'date', required: true },
]
export const ACADEMIC_FIELDS: Record<AcademicEntity, AcademicField[]> = {
  departments: [],
  programs: [
    { key: 'degree_type', label: 'Degree type', required: true },
    { key: 'duration_years', label: 'Duration (years)', type: 'number', required: true, min: 0, step: '0.01' },
    { key: 'total_credits', label: 'Total credits (optional)', type: 'number', step: '0.01' },
  ],
  academic_years: dates,
  semesters: [
    { key: 'semester_number', label: 'Semester number', type: 'number', required: true, min: 1, step: '1' },
    ...dates,
  ],
  courses: [
    { key: 'credits', label: 'Credits (optional)', type: 'number', min: 0, step: '0.01' },
    { key: 'lecture_hours', label: 'Lecture hours (optional)', type: 'number', min: 0, step: '0.01' },
    { key: 'tutorial_hours', label: 'Tutorial hours (optional)', type: 'number', min: 0, step: '0.01' },
    { key: 'practical_hours', label: 'Practical hours (optional)', type: 'number', min: 0, step: '0.01' },
  ],
  program_courses: [],
  course_offerings: [{ key: 'capacity', label: 'Capacity (optional)', type: 'number', min: 1, step: '1' }],
  sections: [{ key: 'capacity', label: 'Capacity (optional)', type: 'number', min: 1, step: '1' }],
}
