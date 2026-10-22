import './__tests__/FacultyStudents.support.tsx'
import { assignment, student } from './__tests__/FacultyStudents.support.tsx'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../../lib/queryClient.ts'
import {
  getFacultyAttendanceAssignments,
  getFacultyAttendanceProfile,
  getFacultyAttendanceStudents,
} from '../../../services/faculty/facultyAttendanceApi.ts'
import { createClassStudentRegistration, type ClassStudentRegistration } from '../../../services/students/studentRegistrationApi.ts'
import FacultyStudents from './FacultyStudents.tsx'
import FacultyStudentsNavigation from './FacultyStudentsNavigation.tsx'
describe('FacultyStudents', () => {
  it('retains the form on duplicate errors and allows correction and retry', async () => {
    vi.mocked(createClassStudentRegistration)
      .mockRejectedValueOnce(new Error('Roster record already exists for this section'))
      .mockResolvedValueOnce({ ...student, student_name: 'Beena Shah', roster_status: 'UNREGISTERED' })
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Beena Shah')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS001')
    await user.type(screen.getByRole('textbox', { name: 'Email (required)' }), 'beena@college.edu')
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    fireEvent.change(screen.getByRole('combobox', { name: 'Batch' }), { target: { value: 'batch-1' } })
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Roster record already exists')
    expect(screen.getByRole('textbox', { name: 'Student name (required)' })).toHaveValue('Beena Shah')
    await user.clear(screen.getByRole('textbox', { name: 'Register number (required)' }))
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS002')
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    fireEvent.change(screen.getByRole('combobox', { name: 'Batch' }), { target: { value: 'batch-1' } })
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    await waitFor(() => expect(screen.queryByRole('form')).not.toBeInTheDocument())
    expect(createClassStudentRegistration).toHaveBeenLastCalledWith('token', 'section-1', {
      student_name: 'Beena Shah',
      register_number: 'CS002',
      email: 'beena@college.edu',
      batch_id: 'batch-1',
    })
  })

  it('blocks blank names and register numbers and discards cancelled changes', async () => {
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), '   ')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), '   ')
    await user.type(screen.getByRole('textbox', { name: 'Email (required)' }), 'beena@college.edu')
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    fireEvent.change(screen.getByRole('combobox', { name: 'Batch' }), { target: { value: 'batch-1' } })
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Enter a student name, register number, and email address.',
    )
    expect(createClassStudentRegistration).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    expect(screen.getByRole('textbox', { name: 'Student name (required)' })).toHaveValue('')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('prevents duplicate submission while a registration is pending', async () => {
    let finish!: (row: ClassStudentRegistration) => void
    vi.mocked(createClassStudentRegistration).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Beena Shah')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS002')
    await user.type(screen.getByRole('textbox', { name: 'Email (required)' }), 'beena@college.edu')
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    fireEvent.change(screen.getByRole('combobox', { name: 'Batch' }), { target: { value: 'batch-1' } })
    await user.dblClick(screen.getByRole('button', { name: 'Register student', exact: true }))
    expect(screen.getByRole('button', { name: 'Registering student…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    expect(screen.getByRole('combobox', { name: 'Section', exact: true })).toBeDisabled()
    expect(screen.getByRole('textbox', { name: 'Register number (required)' })).toBeDisabled()
    expect(createClassStudentRegistration).toHaveBeenCalledTimes(1)
    await act(async () => finish(student))
    await waitFor(() => expect(screen.queryByRole('form')).not.toBeInTheDocument())
  })

  it('hides registration for read-only sections and closes the form when permissions are revoked', async () => {
    const user = userEvent.setup()
    render(
      <>
        <aside>
          <FacultyStudentsNavigation accessToken="token" />
        </aside>
        <FacultyStudents accessToken="token" />
      </>,
    )
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([{ ...assignment, can_manage: false }])
    await act(async () => {
      await queryClient.invalidateQueries({ queryKey: ['faculty', 'students', 'token'] })
    })
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Register new student' })).not.toBeInTheDocument())
    expect(screen.queryByRole('form')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Registration unavailable' })).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'All Student', exact: true }))
    expect(await screen.findByText('Ada Rao')).toBeInTheDocument()
    expect(createClassStudentRegistration).not.toHaveBeenCalled()
  })

  it('chooses an authorized class without selecting a subject and saves its batch', async () => {
    const second = {
      ...assignment,
      section_id: 'section-2',
      section: {
        ...assignment.section,
        section_id: 'section-2',
        name: 'Section B',
        code: 'B',
        course: { name: 'Algorithms', code: 'CS502' },
      },
    }
    const readOnly = {
      ...assignment,
      can_manage: false,
      section_id: 'read-only-section',
      section: { ...assignment.section, section_id: 'read-only-section', name: 'Read only section' },
    }
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment, second, readOnly])
    vi.mocked(createClassStudentRegistration).mockResolvedValue(student)
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    const selector = screen.getByRole('combobox', { name: 'Section', exact: true })
    expect(within(selector).getByRole('option', { name: 'B', exact: true })).toBeInTheDocument()
    expect(within(selector).queryByRole('option', { name: /Read only section/ })).not.toBeInTheDocument()
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Old draft')
    await user.selectOptions(selector, 'section-2')
    expect(window.location.pathname + window.location.search).toBe('/faculty/students/register?section_id=section-2')
    expect(screen.getByRole('form', { name: 'Register student' })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Student name (required)' })).toHaveValue('')
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Beena Shah')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS002')
    await user.type(screen.getByRole('textbox', { name: 'Email (required)' }), 'beena@college.edu')
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    fireEvent.change(screen.getByRole('combobox', { name: 'Batch' }), { target: { value: 'batch-1' } })
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    await waitFor(() =>
      expect(createClassStudentRegistration).toHaveBeenCalledExactlyOnceWith('token', 'section-2', {
        student_name: 'Beena Shah',
        register_number: 'CS002',
        email: 'beena@college.edu',
        batch_id: 'batch-1',
      }),
    )
  })

  it('resets filters and pagination after registration so the full roster is visible', async () => {
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [student], total: 26 })
    vi.mocked(createClassStudentRegistration).mockResolvedValue(student)
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.type(screen.getByRole('searchbox', { name: 'Search students' }), 'Ada')
    await user.click(screen.getByRole('button', { name: 'Search', exact: true }))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Registration status' }), 'ACTIVE')
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Beena Shah')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS002')
    await user.type(screen.getByRole('textbox', { name: 'Email (required)' }), 'beena@college.edu')
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    fireEvent.change(screen.getByRole('combobox', { name: 'Batch' }), { target: { value: 'batch-1' } })
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    await waitFor(() => expect(screen.queryByRole('form')).not.toBeInTheDocument())
    await user.click(await screen.findByRole('button', { name: 'Not now' }))
    expect(screen.getByRole('searchbox', { name: 'Search students' })).toHaveValue('')
    expect(screen.getByRole('combobox', { name: 'Registration status' })).toHaveValue('')
    await waitFor(() => expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('offset')).toBe('0'))
    expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('search')).toBe('')
    expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].has('registration')).toBe(false)
  })

  it('loads the authorized roster and retrieves details only when requested', async () => {
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    expect(await screen.findByText('Ada Rao')).toBeInTheDocument()
    expect(screen.getByText('UNI001')).toBeInTheDocument()
    expect(screen.getByText('80.00%')).toBeInTheDocument()
    expect(getFacultyAttendanceProfile).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'View Ada Rao' }))
    const details = await screen.findByRole('region', { name: 'Student details' })
    expect(await within(details).findByText('2026-10-15')).toBeInTheDocument()
    expect(within(details).getByText('ada@college.edu')).toBeInTheDocument()
    expect(getFacultyAttendanceProfile).toHaveBeenCalledWith('token', 'roster-1', 0)
    await user.click(within(details).getByRole('button', { name: 'Close details' }))
    expect(screen.queryByRole('region', { name: 'Student details' })).not.toBeInTheDocument()
  })
})
