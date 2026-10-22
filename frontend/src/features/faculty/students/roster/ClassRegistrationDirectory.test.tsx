import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ClassRegistrationDirectory from './ClassRegistrationDirectory.tsx'
import { getClassStudentRegistrations, type ClassStudentRegistration } from '../../../../services/students/studentRegistrationApi.ts'

vi.mock('../../../../services/students/studentRegistrationApi.ts', () => ({ getClassStudentRegistrations: vi.fn() }))
const student: ClassStudentRegistration = { registration_id: 'r1', batch_id: 'batch-1', program_id: 'p1', section_code: 'A', batch_start_year: 2026, batch_end_year: 2030,
  student_name: 'Ada Rao', register_number: 'CS001', university_roll_number: null, email: null, roster_status: 'UNREGISTERED', linked_student_id: null, identity_conflict: false, subjects_assigned: false }

beforeEach(() => { vi.resetAllMocks(); vi.mocked(getClassStudentRegistrations).mockResolvedValue({ items: [student], total: 26 }) })

describe('class registration directory', () => {
  it('shows registered students and their admission batch before subject assignment and paginates records', async () => {
    const user = userEvent.setup()
    render(<ClassRegistrationDirectory token="token" sectionId="scope-section" />)
    expect(await screen.findByText('Ada Rao')).toBeInTheDocument()
    expect(screen.getByText('2026–2030')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getByText('Manage in Subject Assignment')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Next registrations' }))
    await waitFor(() => expect(getClassStudentRegistrations).toHaveBeenLastCalledWith('token', 'scope-section', 25, 25, undefined, undefined))
  })

  it('uses the server pending-approval filter before pagination and hides stale records on access errors', async () => {
    vi.mocked(getClassStudentRegistrations).mockResolvedValue({ items: [{ ...student, roster_status: 'PENDING_APPROVAL' }], total: 1 })
    const view = render(<ClassRegistrationDirectory token="token" sectionId="scope-section" waitingApproval />)
    await screen.findByText('Pending approval')
    expect(getClassStudentRegistrations).toHaveBeenCalledWith('token', 'scope-section', 0, 25, 'PENDING_APPROVAL', undefined)
    vi.mocked(getClassStudentRegistrations).mockRejectedValue(new Error('Class scope expired'))
    view.rerender(<ClassRegistrationDirectory token="token" sectionId="another-section" waitingApproval />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Class scope expired')
    expect(screen.queryByText('Ada Rao')).not.toBeInTheDocument()
  })
})
