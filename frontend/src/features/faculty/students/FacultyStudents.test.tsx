import './__tests__/FacultyStudents.support.tsx'
import { assignment, student } from './__tests__/FacultyStudents.support.tsx'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import {
  getFacultyAttendanceAssignments,
  getFacultyAttendanceStudents,
  type FacultyAttendanceRosterRow,
} from '../../../services/faculty/facultyAttendanceApi.ts'
import {
  createClassStudentRegistration,
  getClassStudentRegistrations,
  getRegistrationBatches,
  type ClassStudentRegistration,
} from '../../../services/students/studentRegistrationApi.ts'
import FacultyStudents from './FacultyStudents.tsx'
describe('FacultyStudents', () => {
  it('separates academic filters, keeps batches across class choices and resets incompatible branches', async () => {
    const first = {
      ...assignment,
      section: {
        ...assignment.section,
        semester: { semester_id: 'semester-1', name: 'Semester 1' },
        academic_year: { academic_year_id: 'year-1', name: '2026–2027' },
      },
    }
    const otherSubject = {
      ...first,
      section_id: 'subject-2',
      section: { ...first.section, section_id: 'subject-2', course: { name: 'Mathematics', code: 'MA101' } },
    }
    const nextSemester = {
      ...first,
      section_id: 'semester-2-section',
      semester_id: 'semester-2',
      section: {
        ...first.section,
        section_id: 'semester-2-section',
        semester: { semester_id: 'semester-2', name: 'Semester 2' },
      },
    }
    const otherBranch = {
      ...first,
      section_id: 'ece-section',
      section: {
        ...first.section,
        section_id: 'ece-section',
        program_id: 'program-2',
        program: { ...first.section.program, program_id: 'program-2', name: 'ECE' },
      },
    }
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([first, otherSubject, nextSemester, otherBranch])
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [student], total: 60 })
    vi.mocked(getRegistrationBatches).mockImplementation(async (_token, section) => [
      {
        batch_id: section === 'ece-section' ? 'batch-2' : 'batch-1',
        program_id: section === 'ece-section' ? 'program-2' : 'program-1',
        start_year: 2026,
        end_year: 2030,
        is_active: true,
      },
    ])
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    expect(screen.queryByRole('combobox', { name: 'Section and subject' })).not.toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Course' })).toHaveDisplayValue('B.Tech')
    expect(screen.getByRole('combobox', { name: 'Section', exact: true })).toHaveDisplayValue('Section A')
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    await waitFor(() => expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('offset')).toBe('25'))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Batch' }), 'batch-1')
    await waitFor(() =>
      expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('batch_id')).toBe('batch-1'),
    )
    expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].get('offset')).toBe('0')
    expect(getClassStudentRegistrations).toHaveBeenLastCalledWith('token', 'section-1', 0, 25, undefined, {
      batchId: 'batch-1',
      search: '',
      sort: 'register_number',
    })
    expect(getRegistrationBatches).toHaveBeenCalledWith('token', 'section-1', true)
    await user.selectOptions(screen.getByRole('combobox', { name: 'Subject', exact: true }), 'subject-2')
    expect(window.location.search).toContain('section_id=subject-2')
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toHaveValue('batch-1'))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Semester' }), 'Semester 2 · 2026–2027')
    expect(window.location.search).toContain('section_id=semester-2-section')
    expect(screen.queryByRole('combobox', { name: 'Subject', exact: true })).not.toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Branch' }), 'program-2')
    expect(window.location.search).toContain('section_id=ece-section')
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    expect(screen.getByRole('combobox', { name: 'Batch' })).toHaveValue('')
    await waitFor(() => expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[1]).toBe('ece-section'))
    expect(vi.mocked(getFacultyAttendanceStudents).mock.lastCall?.[2].has('batch_id')).toBe(false)
  })

  it('navigates to a dedicated registration page and returns to the selected roster', async () => {
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.type(screen.getByRole('searchbox', { name: 'Search students' }), 'Ada')
    await user.click(screen.getByRole('button', { name: 'Search', exact: true }))
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    expect(window.location.pathname + window.location.search).toBe('/faculty/students/register?section_id=section-1')
    expect(screen.getByRole('heading', { name: 'Register new student', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Section', exact: true })).toHaveValue('section-1')
    expect(screen.queryByRole('region', { name: 'Student directory' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Back to students' })).not.toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Student name (required)' })).toHaveFocus()
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Unsaved draft')
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(window.location.pathname + window.location.search).toBe('/faculty/students/roster?section_id=section-1')
    expect(screen.getByRole('heading', { name: 'Students', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Section', exact: true })).toHaveValue('A')
    expect(screen.getByRole('searchbox', { name: 'Search students' })).toHaveValue('Ada')
    expect(screen.queryByRole('form', { name: 'Register student' })).not.toBeInTheDocument()
    expect(createClassStudentRegistration).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    expect(screen.getByRole('textbox', { name: 'Student name (required)' })).toHaveValue('')
  })

  it('restores the list and registration page with browser Back and Forward', async () => {
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('Ada Rao')
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    await act(async () => {
      window.history.back()
    })
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Students', level: 1 })).toBeInTheDocument())
    expect(window.location.pathname).toBe('/faculty/students')
    await act(async () => {
      window.history.forward()
    })
    expect(await screen.findByRole('heading', { name: 'Register new student', level: 1 })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/faculty/students/register')
    expect(screen.getByRole('combobox', { name: 'Section', exact: true })).toHaveValue('section-1')
  })

  it('opens and remounts a registration deep link for the requested authorized section', async () => {
    const second = {
      ...assignment,
      section_id: 'section-2',
      section: { ...assignment.section, section_id: 'section-2', name: 'Section B', code: 'B' },
    }
    vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([assignment, second])
    vi.mocked(createClassStudentRegistration).mockResolvedValue(student)
    window.history.replaceState(null, '', '/faculty/students/register?section_id=section-2')
    const first = render(<FacultyStudents accessToken="token" />)
    expect(await screen.findByRole('combobox', { name: 'Section', exact: true })).toHaveValue('section-2')
    first.unmount()
    render(<FacultyStudents accessToken="token" />)
    expect(await screen.findByRole('combobox', { name: 'Section', exact: true })).toHaveValue('section-2')
    const user = userEvent.setup()
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Beena Shah')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS002')
    await user.type(screen.getByRole('textbox', { name: 'Email (required)' }), 'beena@college.edu')
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    fireEvent.change(screen.getByRole('combobox', { name: 'Batch' }), { target: { value: 'batch-1' } })
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    await user.click(await screen.findByRole('button', { name: 'Not now' }))
    await screen.findByRole('heading', { name: 'Students', level: 1 })
    expect(createClassStudentRegistration).toHaveBeenCalledExactlyOnceWith('token', 'section-2', {
      student_name: 'Beena Shah',
      register_number: 'CS002',
      email: 'beena@college.edu',
      batch_id: 'batch-1',
    })
    expect(window.location.pathname + window.location.search).toBe('/faculty/students/roster?section_id=section-2')
  })

  it.each(['unknown-section', 'read-only-section'])(
    'denies registration deep links for %s without falling back to another section',
    async (sectionId) => {
      vi.mocked(getFacultyAttendanceAssignments).mockResolvedValue([
        assignment,
        { ...assignment, section_id: 'read-only-section', can_manage: false },
      ])
      window.history.replaceState(null, '', `/faculty/students/register?section_id=${sectionId}`)
      render(<FacultyStudents accessToken="token" />)
      expect(await screen.findByRole('heading', { name: 'Registration unavailable' })).toBeInTheDocument()
      expect(screen.queryByRole('form', { name: 'Register student' })).not.toBeInTheDocument()
      expect(getFacultyAttendanceStudents).not.toHaveBeenCalled()
      expect(createClassStudentRegistration).not.toHaveBeenCalled()
    },
  )

  it('registers a student in the selected section and refreshes an empty roster', async () => {
    const added: FacultyAttendanceRosterRow & ClassStudentRegistration = {
      ...student,
      roster_id: 'new-roster',
      student_name: 'Beena Shah',
      register_number: 'CS002',
      university_roll_number: 'UNI002',
      email: 'beena@college.edu',
      roster_status: 'UNREGISTERED',
      linked_student_id: null,
      attendance_percentage: null,
    }
    vi.mocked(getFacultyAttendanceStudents).mockResolvedValue({ items: [], total: 0 })
    vi.mocked(createClassStudentRegistration).mockImplementation(async () => {
      vi.mocked(getClassStudentRegistrations).mockResolvedValue({ items: [added], total: 1 })
      return added
    })
    const user = userEvent.setup()
    render(<FacultyStudents accessToken="token" />)
    await screen.findByText('No students in this section yet')
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    const form = screen.getByRole('form', { name: 'Register student' })
    await user.type(within(form).getByRole('textbox', { name: 'Student name (required)' }), ' Beena Shah ')
    await user.type(within(form).getByRole('textbox', { name: 'Register number (required)' }), ' CS002 ')
    await user.type(within(form).getByRole('textbox', { name: 'University roll number' }), ' UNI002 ')
    await user.type(within(form).getByRole('textbox', { name: 'Email (required)' }), 'beena@college.edu')
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
    fireEvent.change(screen.getByRole('combobox', { name: 'Batch' }), { target: { value: 'batch-1' } })
    await user.click(within(form).getByRole('button', { name: 'Register student' }))
    expect(createClassStudentRegistration).toHaveBeenCalledExactlyOnceWith('token', 'section-1', {
      student_name: 'Beena Shah',
      register_number: 'CS002',
      university_roll_number: 'UNI002',
      email: 'beena@college.edu',
      batch_id: 'batch-1',
    })
    await user.click(await screen.findByRole('button', { name: 'Not now' }))
    expect(await screen.findByText('Beena Shah')).toBeInTheDocument()
    expect(
      screen.getByText('Beena Shah was registered in Section A, batch 2026–2030. Subjects can be assigned later.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('form')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Register new student' }))
    expect(screen.getByRole('textbox', { name: 'Student name (required)' })).toHaveValue('')
  })
})
