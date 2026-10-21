import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FacultyStudentRegistration from '../faculty/students/registration/FacultyStudentRegistration.tsx'
import { adminStudentWorkspaceApi as api } from '../../services/admin/adminStudentWorkspaceApi.ts'
import { StudentWorkspaceContext } from './StudentWorkspaceContext.tsx'
import { readStudentFile } from '../admin/students/studentImport.ts'
import type { ClassStudentRegistration } from '../../services/students/studentRegistrationApi.ts'

vi.mock('../../services/admin/adminStudentWorkspaceApi.ts')
vi.mock('../admin/students/studentImport.ts', async (original) => ({ ...await original<typeof import('../admin/students/studentImport.ts')>(), readStudentFile: vi.fn() }))
const assignment = { section_id: 'section', assignment_id: 'assignment', assigned_at: '', academic_year_id: 'year', semester_id: 'semester', can_manage: true, section: { section_id: 'section', name: 'Section A', code: 'A', program_id: 'program', program: { program_id: 'program', name: 'CSE', degree_type: 'B.Tech' }, course: { name: 'Subject', code: 'CS101' } } }
const student: ClassStudentRegistration = { registration_id: 'registration', student_name: 'Ada', email: 'ada@college.edu', register_number: 'CS001', university_roll_number: null, program_id: 'program', batch_id: 'batch', section_code: 'A', batch_start_year: 2026, batch_end_year: 2030, roster_status: 'UNREGISTERED', linked_student_id: null, identity_conflict: false, subjects_assigned: false }
beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(api.getBatches).mockResolvedValue([{ batch_id: 'batch', program_id: 'program', start_year: 2026, end_year: 2030, is_active: true }])
  vi.mocked(api.getRegistrations).mockResolvedValue({ items: [], total: 0 })
  vi.mocked(api.createRegistration).mockResolvedValue(student)
  vi.mocked(api.sendInvitation).mockResolvedValue({ registration_id: 'registration', status: 'sent', message: 'Invitation accepted for delivery.' })
})
const setup = (namespace: 'admin' | 'faculty' = 'admin') => render(<StudentWorkspaceContext.Provider value={{ ...api, namespace }}><FacultyStudentRegistration token="token" assignment={assignment} assignments={[assignment]} onSectionChange={vi.fn()} onRegistered={vi.fn()} onCancel={vi.fn()} /></StudentWorkspaceContext.Provider>)

async function selectBatch() {
  await waitFor(() => expect(screen.getByRole('combobox', { name: 'Batch' })).toBeEnabled())
  fireEvent.change(screen.getByRole('combobox', { name: 'Batch' }), { target: { value: 'batch' } })
}

describe('registration email workflow in the shared registration component', () => {
  it.each(['admin', 'faculty'] as const)('%s requires email, defaults automatic sending off and asks after the save', async (namespace) => {
    const user = userEvent.setup()
    setup(namespace)
    expect(screen.getByRole('checkbox', { name: /Automatically send invitation emails/ })).not.toBeChecked()
    await selectBatch()
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Ada')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS001')
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    expect(api.createRegistration).not.toHaveBeenCalled()
    expect(screen.getByRole('textbox', { name: 'Email (required)' })).toBeRequired()
    await user.type(screen.getByRole('textbox', { name: 'Email (required)' }), 'ada@college.edu')
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    await screen.findByRole('region', { name: 'Student invitation emails' })
    expect(api.createRegistration).toHaveBeenCalledExactlyOnceWith('token', 'section', { student_name: 'Ada', register_number: 'CS001', email: 'ada@college.edu', batch_id: 'batch' })
    expect(api.sendInvitation).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Send invitation email' }))
    await screen.findByText('Invitation accepted for delivery.')
    expect(api.sendInvitation).toHaveBeenCalledExactlyOnceWith('token', 'section', 'registration')
    expect(api.createRegistration).toHaveBeenCalledTimes(1)
  })

  it('sends automatic-delivery consent only when checked and displays the backend delivery result', async () => {
    vi.mocked(api.createRegistration).mockResolvedValue({ ...student, invitation_delivery: { registration_id: 'registration', status: 'failed', message: 'Email unavailable. Student saved.' } })
    const user = userEvent.setup()
    setup()
    await selectBatch()
    await user.type(screen.getByRole('textbox', { name: 'Student name (required)' }), 'Ada')
    await user.type(screen.getByRole('textbox', { name: 'Register number (required)' }), 'CS001')
    await user.type(screen.getByRole('textbox', { name: 'Email (required)' }), 'ada@college.edu')
    await user.click(screen.getByRole('checkbox', { name: /Automatically send invitation emails/ }))
    await user.click(screen.getByRole('button', { name: 'Register student', exact: true }))
    await screen.findByText('Email unavailable. Student saved.')
    expect(vi.mocked(api.createRegistration).mock.lastCall?.[2].auto_send_invitation).toBe(true)
    expect(api.sendInvitation).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Retry unsent invitations' }))
    await screen.findByText('Invitation accepted for delivery.')
    expect(api.createRegistration).toHaveBeenCalledTimes(1)
    expect(api.sendInvitation).toHaveBeenCalledTimes(1)
  })

  it('bulk registration prompts only for successfully saved students and rejects missing email rows', async () => {
    vi.mocked(readStudentFile).mockResolvedValue([
      { row: 2, name: 'Ada', registerNumber: 'CS001', rollNumber: '', email: 'ada@college.edu', attendance: '' },
      { row: 3, name: 'Ben', registerNumber: 'CS002', rollNumber: '', email: 'ben@college.edu', attendance: '' },
      { row: 4, name: 'No Email', registerNumber: 'CS003', rollNumber: '', email: '', attendance: '' },
    ])
    vi.mocked(api.createRegistration).mockResolvedValueOnce(student).mockRejectedValueOnce(new Error('Student save unavailable'))
    const user = userEvent.setup()
    setup()
    await user.click(screen.getByRole('tab', { name: 'Bulk Registration' }))
    await selectBatch()
    fireEvent.change(screen.getByLabelText('Choose student file'), { target: { files: [new File(['content'], 'students.csv')] } })
    await screen.findByText('Student email is required')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Continue to Import' })).toBeEnabled())
    await user.click(screen.getByRole('button', { name: 'Continue to Import' }))
    await user.click(screen.getByRole('button', { name: 'Register 2 students' }))
    const results = await screen.findByRole('region', { name: 'Registration results' })
    expect(within(results).getByRole('status')).toHaveTextContent('Registered: 1 · Failed: 1 · Skipped: 1')
    expect(api.sendInvitation).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Send invitation email' }))
    await screen.findByText('Invitation accepted for delivery.')
    expect(api.sendInvitation).toHaveBeenCalledExactlyOnceWith('token', 'section', 'registration')
    expect(api.createRegistration).toHaveBeenCalledTimes(2)
  })
})
