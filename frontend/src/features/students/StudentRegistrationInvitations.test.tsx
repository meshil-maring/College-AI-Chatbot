import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudentRegistrationInvitations from './StudentRegistrationInvitations.tsx'
import { sendStudentRegistrationInvitation, type ClassStudentRegistration, type StudentInvitationDelivery } from '../../services/students/studentRegistrationApi.ts'
import { AdminApiError } from '../../services/admin/adminApi.ts'

vi.mock('../../services/students/studentRegistrationApi.ts', () => ({ sendStudentRegistrationInvitation: vi.fn() }))
const students = ['Ada', 'Ben'].map((name, index): ClassStudentRegistration => ({ registration_id: `r${index + 1}`, student_name: name, email: `${name.toLowerCase()}@college.edu`, register_number: `CS${index}`, university_roll_number: null, batch_id: 'batch', batch_start_year: 2026, batch_end_year: 2030, section_code: 'A', program_id: 'program', roster_status: 'UNREGISTERED', linked_student_id: null, identity_conflict: false, subjects_assigned: false }))
beforeEach(() => vi.resetAllMocks())

describe('student invitation consent and results', () => {
  it('asks after registration and sends nothing when Not now is selected', async () => {
    const user = userEvent.setup()
    render(<StudentRegistrationInvitations token="token" sectionId="section" students={students} />)
    expect(screen.getByText('Send registration invitations to all 2 registered students?')).toBeInTheDocument()
    expect(sendStudentRegistrationInvitation).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Not now' }))
    expect(sendStudentRegistrationInvitation).not.toHaveBeenCalled()
    expect(screen.queryByRole('region', { name: 'Student invitation emails' })).not.toBeInTheDocument()
  })

  it('sends once per saved student and retries only failed invitation emails', async () => {
    let finish!: (value: StudentInvitationDelivery) => void
    vi.mocked(sendStudentRegistrationInvitation).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
      .mockRejectedValueOnce(new Error('Mail unavailable'))
      .mockResolvedValueOnce({ registration_id: 'r2', status: 'sent', message: 'Accepted for delivery' })
    const user = userEvent.setup()
    render(<StudentRegistrationInvitations token="token" sectionId="section" students={students} />)
    await user.dblClick(screen.getByRole('button', { name: 'Send invitations to all' }))
    expect(sendStudentRegistrationInvitation).toHaveBeenCalledTimes(1)
    await act(async () => finish({ registration_id: 'r1', status: 'sent', message: 'Accepted for delivery' }))
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Accepted for delivery: 1 · Failed: 1'))
    expect(sendStudentRegistrationInvitation).toHaveBeenCalledTimes(2)
    await user.click(screen.getByRole('button', { name: 'Retry unsent invitations' }))
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Accepted for delivery: 2 · Failed: 0'))
    expect(sendStudentRegistrationInvitation).toHaveBeenCalledTimes(3)
    expect(sendStudentRegistrationInvitation).toHaveBeenLastCalledWith('token', 'section', 'r2')
  })

  it('preserves automatic delivery results and retries the failed email without resending successes', async () => {
    vi.mocked(sendStudentRegistrationInvitation).mockResolvedValue({ registration_id: 'r2', status: 'captured', message: 'Email captured locally; it has not been delivered to the student.' })
    const user = userEvent.setup()
    render(<StudentRegistrationInvitations token="token" sectionId="section" students={[
      { ...students[0], invitation_delivery: { registration_id: 'r1', status: 'sent', message: 'Accepted' } },
      { ...students[1], invitation_delivery: { registration_id: 'r2', status: 'failed', message: 'Could not send' } },
    ]} />)
    await user.click(screen.getByRole('button', { name: 'Retry unsent invitations' }))
    await screen.findByText('Email captured locally; it has not been delivered to the student.')
    expect(sendStudentRegistrationInvitation).toHaveBeenCalledExactlyOnceWith('token', 'section', 'r2')
    expect(screen.getByRole('status')).toHaveTextContent('Accepted for delivery: 1')
  })

  it('stops sending further emails after access is revoked', async () => {
    vi.mocked(sendStudentRegistrationInvitation).mockRejectedValue(new AdminApiError(403, 'Access revoked'))
    const user = userEvent.setup()
    render(<StudentRegistrationInvitations token="token" sectionId="section" students={students} />)
    await user.click(screen.getByRole('button', { name: 'Send invitations to all' }))
    await screen.findByText('Not attempted: Access revoked')
    expect(sendStudentRegistrationInvitation).toHaveBeenCalledTimes(1)
  })

  it('shows the provider configuration error and allows retrying only the saved invitation', async () => {
    const message = 'The email provider rejected the sending credentials (HTTP 401). Ask your administrator to check the sending API key, domain and region before retrying. The student is already registered.'
    vi.mocked(sendStudentRegistrationInvitation)
      .mockResolvedValueOnce({ registration_id: 'r1', status: 'failed', message })
      .mockResolvedValueOnce({ registration_id: 'r1', status: 'sent', message: 'Invitation email accepted for delivery.' })
    const user = userEvent.setup()
    render(<StudentRegistrationInvitations token="token" sectionId="section" students={[students[0]]} />)
    await user.click(screen.getByRole('button', { name: 'Send invitation email' }))
    expect(await screen.findByText(message)).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Failed: 1')
    await user.click(screen.getByRole('button', { name: 'Retry unsent invitations' }))
    expect(await screen.findByText('Invitation email accepted for delivery.')).toBeInTheDocument()
    expect(sendStudentRegistrationInvitation).toHaveBeenCalledTimes(2)
    expect(sendStudentRegistrationInvitation).toHaveBeenLastCalledWith('token', 'section', 'r1')
  })
})
