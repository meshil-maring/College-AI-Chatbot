import './__tests__/FacultyAttendance.support.tsx'
import { assignment, overview, roster } from './__tests__/FacultyAttendance.support.tsx'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import {
  commitFacultyAttendanceImport,
  getFacultyAttendanceAssignments,
  getFacultyAttendanceImports,
  getFacultyAttendanceOverview,
  getFacultyAttendanceSessions,
  getFacultyAttendanceStudents,
  markFacultyAttendance,
  uploadFacultyAttendance,
} from '../../../services/faculty/facultyAttendanceApi.ts'
import FacultyAttendance from './FacultyAttendance.tsx'
describe('FacultyAttendance', () => {
  it('bulk marks a roster and permits an individual change before submission', async () => {
    const user = userEvent.setup()
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Mark Attendance' }))
    await user.click(screen.getByRole('button', { name: 'Mark all present' }))
    await user.selectOptions(screen.getByLabelText('Attendance for Rahul Sharma'), 'absent')
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({
      items: [{ ...roster[0], attendance_percentage: 89.29, present: 25, absent: 3 }],
      total: 1,
    })
    vi.mocked(getFacultyAttendanceOverview).mockResolvedValue({
      ...overview,
      average_attendance: 89.29,
      present: 25,
      absent: 3,
    })
    await user.click(screen.getByRole('button', { name: 'Save Attendance' }))
    await waitFor(() =>
      expect(markFacultyAttendance).toHaveBeenCalledWith('token', 'section-1', expect.any(String), {
        'roster-1': 'absent',
      }),
    )
    expect(await screen.findByText('1 attendance records saved.')).toBeInTheDocument()
    await waitFor(() => expect(getFacultyAttendanceStudents).toHaveBeenCalledTimes(2))
    expect(getFacultyAttendanceOverview).toHaveBeenCalledTimes(2)
    expect(getFacultyAttendanceAssignments).toHaveBeenCalledTimes(1)
    expect(await screen.findByText('89.29%')).toBeInTheDocument()
  })

  it('does not submit a student changed back to not marked', async () => {
    const user = userEvent.setup()
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Mark Attendance' }))
    await user.selectOptions(screen.getByLabelText('Attendance for Rahul Sharma'), 'present')
    await user.selectOptions(screen.getByLabelText('Attendance for Rahul Sharma'), '')
    await user.click(screen.getByRole('button', { name: 'Save Attendance' }))
    expect(markFacultyAttendance).not.toHaveBeenCalled()
  })

  it('shows subject-specific profile history from the server', async () => {
    const user = userEvent.setup()
    render(<FacultyAttendance accessToken="token" />)
    await user.click(await screen.findByRole('button', { name: 'View' }))
    const modal = screen.getByRole('dialog', { name: 'Student Attendance Profile' })
    expect(await within(modal).findByText('2026-10-07')).toBeInTheDocument()
    expect(within(modal).getByText(/this subject only/)).toBeInTheDocument()
  })

  it.each(['HOD', 'Class In-Charge'])('keeps %s monitoring read-only', async () => {
    const user = userEvent.setup()
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([{ ...assignment, can_manage: false }])
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    expect(screen.getByText(/Monitoring access/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mark Attendance' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Upload Attendance' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Import History' }))
    expect(await screen.findByText('No imports are available for this subject.')).toBeInTheDocument()
  })

  it('displays real sessions and import history', async () => {
    const user = userEvent.setup()
    vi.mocked(getFacultyAttendanceImports).mockResolvedValue([
      {
        import_id: 'import-1',
        original_filename: 'roster.csv',
        uploaded_by: 'faculty-1',
        created_at: '2026-10-07T00:00:00Z',
        status: 'IMPORTED',
        summary: { total_rows: 1, imported: 1 },
      },
    ])
    vi.mocked(getFacultyAttendanceSessions).mockResolvedValue({
      items: [
        {
          session_id: 'session-1',
          session_date: '2026-10-07',
          record_count: 1,
          present: 1,
          absent: 0,
          attendance_percentage: 100,
        },
      ],
      total: 1,
    })
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Import History' }))
    expect(await screen.findByText('roster.csv')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Session-wise View' }))
    expect(await screen.findByText('2026-10-07')).toBeInTheDocument()
  })

  it('shows permission denial without stale student data', async () => {
    vi.mocked(getFacultyAttendanceStudents).mockRejectedValue(new Error('Your teaching assignment is no longer valid'))
    render(<FacultyAttendance accessToken="token" />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Your teaching assignment is no longer valid')
    expect(screen.queryByText('Rahul Sharma')).not.toBeInTheDocument()
  })

  it('refreshes context after revocation and removes the roster', async () => {
    const { rerender } = render(<FacultyAttendance accessToken="token" scopeVersion="initial" />)
    await screen.findByText('Rahul Sharma')
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([])
    rerender(<FacultyAttendance accessToken="token" scopeVersion="revoked" />)
    expect(await screen.findByText('No Active Assignments')).toBeInTheDocument()
    expect(screen.queryByText('Rahul Sharma')).not.toBeInTheDocument()
  })

  it('loads every server page instead of truncating at the REST row cap', async () => {
    const first = Array.from({ length: 500 }, (_, index) => ({
      ...roster[0],
      roster_id: `r-${index}`,
      register_number: `R${index}`,
      student_name: `Student ${index}`,
    }))
    vi.mocked(getFacultyAttendanceStudents)
      .mockResolvedValueOnce({ items: first, total: 501 })
      .mockResolvedValueOnce({ items: [{ ...roster[0], student_name: 'Final Student' }], total: 501 })
    render(<FacultyAttendance accessToken="token" />)
    await waitFor(() => expect(getFacultyAttendanceStudents).toHaveBeenCalledTimes(2))
    const args = vi.mocked(getFacultyAttendanceStudents).mock.calls[1]
    expect(args[2].get('offset')).toBe('500')
    expect(await screen.findByText(/of 501 students/)).toBeInTheDocument()
  })

  it.each(['ERROR', 'CONFLICT', 'DUPLICATE'])('blocks committing %s rows', async (state) => {
    const user = userEvent.setup()
    vi.mocked(uploadFacultyAttendance).mockResolvedValue({
      import_id: 'import-1',
      summary: {
        total_rows: 2,
        valid: 1,
        errors: state === 'ERROR' ? 1 : 0,
        conflicts: state === 'CONFLICT' ? 1 : 0,
        duplicates: state === 'DUPLICATE' ? 1 : 0,
      },
      rows: [
        {
          row_number: 2,
          normalized_data: { student_name: 'Ada' },
          validation_status: state,
          errors: ['Identity issue'],
        },
      ],
    })
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Upload Attendance' }))
    await user.upload(
      screen.getByLabelText('Attendance file'),
      new File(['data'], 'attendance.csv', { type: 'text/csv' }),
    )
    await user.click(screen.getByRole('button', { name: 'Process File' }))
    await user.click(await screen.findByRole('button', { name: 'Continue to Review' }))
    expect(screen.getByRole('button', { name: 'Import 1 Valid Records' })).toBeDisabled()
    expect(commitFacultyAttendanceImport).not.toHaveBeenCalled()
  })

  it('asks for OCR/AI consent only when the server requires it', async () => {
    const user = userEvent.setup()
    vi.mocked(uploadFacultyAttendance).mockRejectedValueOnce(
      Object.assign(new Error('Confirmation required'), { code: 'AI_CONFIRMATION_REQUIRED' }),
    )
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Upload Attendance' }))
    await user.upload(screen.getByLabelText('Attendance file'), new File(['image'], 'scan.png', { type: 'image/png' }))
    await user.click(screen.getByRole('button', { name: 'Process File' }))
    expect(await screen.findByText('AI Processing May Be Required')).toBeInTheDocument()
    expect(screen.getByText(/AI processing can consume tokens/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Continue' }))
    await waitFor(() =>
      expect(uploadFacultyAttendance).toHaveBeenLastCalledWith(
        'token',
        'section-1',
        'semester-1',
        expect.any(File),
        true,
      ),
    )
  })

  it('shows import network errors and keeps the upload available', async () => {
    const user = userEvent.setup()
    vi.mocked(uploadFacultyAttendance).mockRejectedValue(new Error('OCR is unavailable; use CSV/XLSX'))
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Upload Attendance' }))
    await user.upload(
      screen.getByLabelText('Attendance file'),
      new File(['data'], 'scan.pdf', { type: 'application/pdf' }),
    )
    await user.click(screen.getByRole('button', { name: 'Process File' }))
    expect(await screen.findByRole('button', { name: 'Process File' })).toBeInTheDocument()
    expect(screen.getAllByText('OCR is unavailable; use CSV/XLSX').length).toBeGreaterThan(0)
  })
})
