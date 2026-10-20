import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudentApprovalQueue from './StudentApprovalQueue.tsx'
import { approvePendingStudent, listPendingStudents, rejectPendingStudent } from '../../services/adminApi.ts'
import type { PendingStudent } from '../../types/admin.ts'

vi.mock('../../services/adminApi.ts', async (original) => ({
  ...await original<typeof import('../../services/adminApi.ts')>(),
  listPendingStudents: vi.fn(), approvePendingStudent: vi.fn(), rejectPendingStudent: vi.fn(),
}))

const pending: PendingStudent[] = Array.from({ length: 26 }, (_, index) => ({
  student_id: `private-student-${index}`, user_id: `private-user-${index}`, institution_id: 'private-institution',
  student_number: `STU-${index + 1}`, register_number: `REG-${index + 1}`, university_roll_number: null,
  email: `student-${index + 1}@college.test`, approval_status: 'pending', status: 'active', is_active: true,
  enrollment_date: null, created_at: '', updated_at: '',
}))

beforeEach(() => { vi.resetAllMocks(); vi.mocked(listPendingStudents).mockResolvedValue(pending) })

describe('shared student approvals', () => {
  it.each(['admin', 'staff'] as const)('uses the same search and pagination workflow for %s', async (namespace) => {
    const user = userEvent.setup()
    render(<StudentApprovalQueue accessToken="token" namespace={namespace} />)
    await screen.findByText('STU-1')
    expect(screen.queryByText('STU-26')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Next registration page' }))
    expect(screen.getByText('STU-26')).toBeInTheDocument()
    await user.type(screen.getByRole('searchbox', { name: 'Search pending registrations' }), 'student-1@college.test')
    expect(screen.getByText('STU-26')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Search', exact: true }))
    expect(screen.getByText('STU-1')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Previous registration page' })).toBeDisabled()
    expect(screen.queryByText('private-institution')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(26)
  })

  it('only exposes permitted decisions and prevents duplicate approval submissions', async () => {
    const user = userEvent.setup()
    vi.mocked(listPendingStudents).mockResolvedValue([pending[0]])
    let finish!: (student: PendingStudent) => void
    vi.mocked(approvePendingStudent).mockImplementation(() => new Promise((resolve) => { finish = resolve }))
    render(<StudentApprovalQueue accessToken="token" namespace="staff" canApprove canReject={false} />)
    await screen.findByText('STU-1')
    expect(screen.queryByRole('button', { name: 'Reject' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    await waitFor(() => expect(approvePendingStudent).toHaveBeenCalledOnce())
    expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled()
    finish({ ...pending[0], approval_status: 'approved' })
    expect(await screen.findByText('No students are awaiting approval right now.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Refresh registrations' }))
    expect(rejectPendingStudent).not.toHaveBeenCalled()
  })
})
