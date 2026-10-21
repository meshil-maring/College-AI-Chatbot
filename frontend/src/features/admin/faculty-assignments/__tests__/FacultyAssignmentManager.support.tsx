import { vi } from 'vitest'

vi.mock('../../../../services/admin/adminApi.ts')

export const assignmentData = {
  sections: [
    {
      section_id: 'section-1',
      name: 'Section A',
      code: 'A',
      course: { name: 'Mathematics', code: 'MATH101' },
    },
  ],
  faculty: [
    {
      id: 'faculty-1',
      email: 'faculty@example.test',
      first_name: 'Ada',
      last_name: 'Lovelace',
    },
  ],
  assignments: [
    {
      assignment_id: 'assignment-1',
      faculty_user_id: 'faculty-1',
      section_id: 'section-1',
      start_at: '2000-01-01T00:00:00Z',
      end_at: null,
      is_active: true,
      faculty: { email: 'faculty@example.test', first_name: 'Ada', last_name: 'Lovelace' },
      section: { name: 'Section A', code: 'A', course: { name: 'Mathematics', code: 'MATH101' } },
    },
  ],
}
