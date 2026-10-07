/// <reference types="vitest/globals" />
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FacultyAttendance from './FacultyAttendance.tsx'
import {
  commitFacultyAttendanceImport,
  getFacultyAttendanceAssignments,
  getFacultyAttendanceRoster,
  uploadFacultyAttendance,
} from '../../services/facultyAttendanceApi.ts'

vi.mock('../../services/facultyAttendanceApi.ts', () => ({
  commitFacultyAttendanceImport: vi.fn(),
  getFacultyAttendanceAssignments: vi.fn(),
  getFacultyAttendanceRoster: vi.fn(),
  markFacultyAttendance: vi.fn(),
  uploadFacultyAttendance: vi.fn(),
}))

const assignment = {
  assignment_id: 'assignment-1',
  assigned_at: '2026-10-06T00:00:00Z',
  section_id: 'section-1',
  semester_id: 'semester-1',
  academic_year_id: 'year-1',
  section: { section_id: 'section-1', name: 'Section A', code: 'A', course: { name: 'Data Mining', code: 'CS-501' } },
}

const roster = [{
  roster_id: 'roster-1',
  register_number: 'CSE23-001',
  university_roll_number: '2023CSE001',
  student_name: 'Rahul Sharma',
  email: 'rahul@example.com',
  address: null,
  roster_status: 'ACTIVE' as const,
  linked_student_id: 'student-1',
  imported_summary: { attendance_percentage: 92.86, total_classes: 28, present_classes: 26, absent_classes: 2 },
}]

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment])
  vi.mocked(getFacultyAttendanceRoster).mockResolvedValue(roster)
  vi.mocked(uploadFacultyAttendance).mockResolvedValue({ import_id: 'import-1', summary: { total_rows: 1, valid: 1, new_records: 1, updates: 0, errors: 0 }, rows: [{ row_number: 2, normalized_data: { student_name: 'Rahul Sharma' }, validation_status: 'NEW', errors: [] }] })
  vi.mocked(commitFacultyAttendanceImport).mockResolvedValue({ imported_rows: 1 })
})

describe('FacultyAttendance', () => {
  it('renders an honest empty state when the faculty has no assignments', async () => {
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([])
    render(<FacultyAttendance accessToken="token" />)
    expect(await screen.findByRole('heading', { name: 'No Active Assignments' })).toBeInTheDocument()
    expect(screen.queryByText('42')).not.toBeInTheDocument()
  })

  it('renders authorized roster data and opens manual attendance', async () => {
    const user = userEvent.setup()
    render(<FacultyAttendance accessToken="token" />)
    expect(await screen.findByText('Rahul Sharma')).toBeInTheDocument()
    expect(screen.getAllByText('92.86%').length).toBeGreaterThan(0)
    expect(screen.getByRole('combobox', { name: 'Department / Program' })).toHaveValue('CS-501 · Data Mining')
    await user.click(screen.getByRole('button', { name: 'Mark Attendance' }))
    expect(screen.getByRole('dialog', { name: 'Mark Attendance' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Attendance for Rahul Sharma' })).toBeInTheDocument()
  })

  it('keeps upload review and commit behind the explicit workflow', async () => {
    const user = userEvent.setup()
    render(<FacultyAttendance accessToken="token" />)
    await user.click(await screen.findByRole('button', { name: 'Upload Attendance' }))
    const file = new File(['register_number,student_name\nCSE23-001,Rahul Sharma'], 'attendance.csv', { type: 'text/csv' })
    await user.upload(screen.getByLabelText('Attendance file'), file)
    await user.click(screen.getByRole('button', { name: 'Process File' }))
    expect(await screen.findByText(/File processed successfully/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Import 1 Valid Records' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Import 1 Valid Records' }))
    expect(await screen.findByText('Attendance Imported Successfully')).toBeInTheDocument()
    expect(commitFacultyAttendanceImport).toHaveBeenCalledWith('token', 'import-1')
  })
})
