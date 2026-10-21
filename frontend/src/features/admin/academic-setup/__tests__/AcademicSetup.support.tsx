import { fireEvent, screen, within } from '@testing-library/react'
import { beforeEach, vi } from 'vitest'
import * as api from '../../../../services/admin/adminApi.ts'
import type { AcademicCatalogue } from '../../../../types/academicSetup.ts'
vi.mock('../../../../services/admin/adminApi.ts')

export const fixture = (): AcademicCatalogue => ({
  institution_id: 'tenant',
  manageable: [
    'departments',
    'programs',
    'academic_years',
    'semesters',
    'courses',
    'program_courses',
    'course_offerings',
    'sections',
    'batches',
  ],
  records: {
    batches: [],
    departments: [
      { department_id: 'd', name: 'Science', code: 'SCI', is_active: true },
      { department_id: 'inactive', name: 'Archived', code: 'OLD', is_active: false },
    ],
    programs: [
      { program_id: 'p', department_id: 'd', name: 'Science degree', code: 'BS', is_active: true },
      { program_id: 'blocked', department_id: 'inactive', name: 'Unavailable', code: 'BAD', is_active: true },
    ],
    academic_years: [
      {
        academic_year_id: 'y',
        name: '2026-27',
        code: 'Y26',
        start_date: '2026-07-01',
        end_date: '2027-06-30',
        is_active: true,
      },
    ],
    semesters: [
      { semester_id: 's', academic_year_id: 'y', name: 'Semester 1', code: 'S1', is_active: true },
      { semester_id: 'other', academic_year_id: 'other-year', name: 'Foreign term', code: 'OTHER', is_active: true },
    ],
    courses: [
      { course_id: 'c', department_id: 'd', name: 'Mathematics', code: 'MATH', is_active: true },
      { course_id: 'not-linked', department_id: 'd', name: 'Physics', code: 'PHY', is_active: true },
    ],
    program_courses: [
      {
        program_course_id: 'pc',
        program_id: 'p',
        course_id: 'c',
        semester_id: null,
        course_type: 'core',
        is_required: true,
        is_active: true,
      },
    ],
    course_offerings: [
      {
        course_offering_id: 'o',
        program_id: 'p',
        course_id: 'c',
        academic_year_id: 'y',
        semester_id: 's',
        is_active: true,
      },
    ],
    sections: [],
  },
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getAcademicCatalogue).mockResolvedValue(fixture())
  vi.mocked(api.saveAcademicRecord).mockResolvedValue({ saved: true })
})

export async function loaded() {
  await screen.findByRole('button', { name: /^Add record$/ })
}

export function tab(name: string) {
  fireEvent.click(
    within(screen.getByRole('navigation', { name: 'Academic setup entities' })).getByRole('button', {
      name: new RegExp(`^${name}`),
    }),
  )
}
