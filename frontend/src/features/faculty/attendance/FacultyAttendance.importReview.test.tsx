import './__tests__/FacultyAttendance.support.tsx'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import {
  commitFacultyAttendanceImport,
  correctFacultyAttendanceImportRow,
  getFacultyAttendanceAssignments,
  getFacultyAttendanceImportReview,
  getFacultyAttendanceImports,
  getFacultyAttendanceOverview,
  getFacultyAttendanceStudents,
  uploadFacultyAttendance,
} from '../../../services/faculty/facultyAttendanceApi.ts'
import FacultyAttendance from './FacultyAttendance.tsx'
describe('FacultyAttendance', () => {
  it('revalidates corrected staging values before committing', async () => {
    const user = userEvent.setup()
    vi.mocked(uploadFacultyAttendance).mockResolvedValue({
      import_id: 'import-1',
      summary: { total_rows: 1, valid: 0, errors: 1 },
      rows: [
        {
          row_number: 2,
          normalized_data: { register_number: 'R1', student_name: 'Ada', attendance_percentage: '200' },
          validation_status: 'ERROR',
          errors: ['Percentage out of range'],
        },
      ],
    })
    vi.mocked(correctFacultyAttendanceImportRow).mockResolvedValue({
      import_id: 'import-1',
      status: 'REVIEWED',
      summary: { total_rows: 1, valid: 1, errors: 0 },
      rows: [
        {
          row_number: 2,
          normalized_data: { register_number: 'R1', student_name: 'Ada', attendance_percentage: '70' },
          validation_status: 'NEW',
          errors: [],
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
    await user.click(screen.getByText('Values / correction'))
    const field = screen.getByLabelText('attendance_percentage row 2')
    await user.clear(field)
    await user.type(field, '70')
    await user.click(screen.getByRole('button', { name: 'Save correction and validate again' }))
    await waitFor(() =>
      expect(correctFacultyAttendanceImportRow).toHaveBeenCalledWith(
        'token',
        'import-1',
        2,
        expect.objectContaining({ attendance_percentage: '70' }),
      ),
    )
    expect(await screen.findByRole('button', { name: 'Import 1 Valid Records' })).toBeEnabled()
  })

  it('opens an imported history review without enabling commit', async () => {
    const user = userEvent.setup()
    vi.mocked(getFacultyAttendanceImports).mockResolvedValue([
      {
        import_id: 'import-1',
        original_filename: 'done.csv',
        uploaded_by: 'faculty-1',
        created_at: '2026-10-07T00:00:00Z',
        status: 'IMPORTED',
        summary: { total_rows: 1, imported: 1 },
      },
    ])
    vi.mocked(getFacultyAttendanceImportReview).mockResolvedValue({
      import_id: 'import-1',
      status: 'IMPORTED',
      summary: { total_rows: 1, valid: 1, errors: 0 },
      rows: [{ row_number: 2, normalized_data: { student_name: 'Ada' }, validation_status: 'NEW', errors: [] }],
    })
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    await user.click(screen.getByRole('button', { name: 'Import History' }))
    await user.click(await screen.findByRole('button', { name: 'Review' }))
    expect(await screen.findByRole('button', { name: 'Already Imported' })).toBeDisabled()
  })

  it('supports keyboard dialog close and restores focus', async () => {
    const user = userEvent.setup()
    render(<FacultyAttendance accessToken="token" />)
    await screen.findByText('Rahul Sharma')
    const opener = screen.getByRole('button', { name: 'Mark Attendance' })
    await user.click(opener)
    expect(screen.getByRole('dialog', { name: 'Mark Attendance' })).toHaveFocus()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(opener).toHaveFocus()
  })

  it('keeps upload review and commit behind the explicit workflow', async () => {
    const user = userEvent.setup()
    render(<FacultyAttendance accessToken="token" />)
    await user.click(await screen.findByRole('button', { name: 'Upload Attendance' }))
    const file = new File(['register_number,student_name\nCSE23-001,Rahul Sharma'], 'attendance.csv', {
      type: 'text/csv',
    })
    await user.upload(screen.getByLabelText('Attendance file'), file)
    await user.click(screen.getByRole('button', { name: 'Process File' }))
    expect(await screen.findByText(/File processed successfully/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Required Fields' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Continue to Review' }))
    expect(screen.getByRole('button', { name: 'Import 1 Valid Records' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Import 1 Valid Records' }))
    expect(await screen.findByText('Attendance Imported Successfully')).toBeInTheDocument()
    expect(commitFacultyAttendanceImport).toHaveBeenCalledWith('token', 'import-1')
    await waitFor(() => expect(getFacultyAttendanceStudents).toHaveBeenCalledTimes(2))
    expect(getFacultyAttendanceOverview).toHaveBeenCalledTimes(2)
    expect(getFacultyAttendanceAssignments).toHaveBeenCalledTimes(1)
  })
})
