import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, vi } from 'vitest'
import type { MarksDetail, TestImport } from '../../../../services/faculty/facultyTestsApi.ts'
import * as api from '../../../../services/faculty/facultyTestsApi.ts'
import FacultyTests from '../FacultyTests.tsx'
vi.mock('../../../../services/faculty/facultyTestsApi.ts')

export const scope = {
  section_id: 'section-1',
  name: 'Section A',
  code: 'A',
  semester_id: 'semester-1',
  department_id: 'department-1',
  program_id: 'program-1',
  academic_year_id: 'year-1',
  can_manage: true,
  department: { department_id: 'department-1', name: 'CSE' },
  program: { program_id: 'program-1', name: 'B.Tech' },
  academic_year: { academic_year_id: 'year-1', name: '2026–27' },
  semester: { semester_id: 'semester-1', name: 'Semester 5' },
  course: { name: 'Data Mining', code: 'DM' },
}

export const detail: MarksDetail = {
  test: {
    test_id: 'test-1',
    section_id: scope.section_id,
    title: 'Class test',
    test_type: 'class_test',
    description: 'Assessment instructions',
    max_marks: 100,
    passing_marks: 40,
    scheduled_date: '2026-10-07',
    start_time: null,
    end_time: null,
    duration_minutes: null,
    status: 'COMPLETED',
    marks_state: 'DRAFT',
    version: 3,
    created_by: 'faculty-1',
    created_at: '2026-10-07T08:00:00Z',
    updated_at: '2026-10-07T08:00:00Z',
    can_manage: true,
    section: scope,
  },
  rows: [
    {
      roster_id: 'roster-1',
      register_number: 'R1',
      university_roll_number: 'U1',
      student_name: 'Ada Student',
      roster_status: 'ACTIVE',
      reconciliation_state: 'LINKED',
      mark_status: 'present',
      scored_marks: 75,
      percentage: 75,
      outcome: 'pass',
      remarks: null,
    },
    {
      roster_id: 'roster-2',
      register_number: 'R2',
      university_roll_number: null,
      student_name: 'Grace Student',
      roster_status: 'UNREGISTERED',
      reconciliation_state: 'NONE',
      mark_status: 'absent',
      scored_marks: null,
      percentage: null,
      outcome: null,
      remarks: null,
    },
  ],
  review: {
    total: 2,
    entered: 2,
    missing: 0,
    absent: 1,
    exempt: 0,
    not_attempted: 0,
    conflicts: 0,
    pass: 1,
    fail: 0,
    average_percentage: 75,
  },
}

export const imported: TestImport = {
  import_id: 'import-1',
  test_id: 'test-1',
  original_filename: 'marks.csv',
  uploaded_by: 'faculty-1',
  status: 'VALIDATED',
  updated_at: '2026-10-07T08:30:00Z',
  created_at: '2026-10-07T08:30:00Z',
  summary: { valid: 1, errors: 0, total_rows: 1 },
  rows: [
    {
      row_number: 2,
      raw_data: { register_number: 'R1', mark_status: 'present', scored_marks: '90' },
      normalized_data: { register_number: 'R1', mark_status: 'present', scored_marks: '90' },
      validation_status: 'VALID',
      errors: [],
      warnings: [],
    },
  ],
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(api.getTestResources).mockResolvedValue([scope])
  vi.mocked(api.getTestTypes).mockResolvedValue([{ code: 'class_test', name: 'Class Test' }])
  vi.mocked(api.getTests).mockResolvedValue({
    items: [detail.test],
    total: 1,
    overview: { upcoming: 0, draft: 0, completed: 1, pending_marks: 1, published: 0, locked: 0 },
  })
  vi.mocked(api.getTest).mockResolvedValue(structuredClone(detail))
  vi.mocked(api.createTest).mockResolvedValue({ ...detail.test, status: 'DRAFT', version: 1 })
  vi.mocked(api.transitionTest).mockResolvedValue(detail.test)
  vi.mocked(api.saveTestMarks).mockResolvedValue({ version: 4 })
  vi.mocked(api.uploadTestMarks).mockResolvedValue(structuredClone(imported))
  vi.mocked(api.correctTestImport).mockResolvedValue(structuredClone(imported))
  vi.mocked(api.commitTestImport).mockResolvedValue({ version: 4 })
  vi.mocked(api.getTestImport).mockResolvedValue({ ...imported, status: 'IMPORTED' })
  vi.mocked(api.getTestHistory).mockResolvedValue({ imports: [], events: [] })
})

export async function open() {
  const user = userEvent.setup()
  render(<FacultyTests accessToken="token" />)
  await user.click(await screen.findByRole('button', { name: 'Open Class test' }, { timeout: 5000 }))
  await screen.findByRole('heading', { name: 'Result review' })
  return user
}
