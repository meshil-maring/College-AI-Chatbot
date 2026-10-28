import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from './StaffFacultyManager.tsx'
import * as api from '../../../services/admin/adminApi.ts'

vi.mock('../../../services/admin/adminApi.ts', () => ({
  listMembershipRequests: vi.fn(),
  listMembershipRoster: vi.fn(),
  decideMembershipRequest: vi.fn(),
  changeMembershipStatus: vi.fn(),
}))

const request = {
  request_id: '10000000-0000-0000-0000-000000000001',
  full_name: 'Ada Faculty',
  email: 'ada@example.test',
  requested_role: 'faculty' as const,
  status: 'pending' as const,
  created_at: '2026-10-04T00:00:00Z',
}

describe('StaffFacultyManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listMembershipRequests).mockResolvedValue({ requests: [request], total: 1 })
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [], total: 0 })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  it('shows tenant-safe requests and the empty roster state', async () => {
    render(<StaffFacultyManager accessToken="jwt" />)
    expect(await screen.findByText('Ada Faculty')).toBeDefined()
    expect(screen.getByText('No staff or faculty are on the roster yet.')).toBeDefined()
    expect(api.listMembershipRequests).toHaveBeenCalledWith('jwt', undefined, 'pending')
  })

  it('waits for server approval and reloads instead of changing optimistically', async () => {
    vi.mocked(api.decideMembershipRequest).mockResolvedValue({
      request_id: request.request_id,
      status: 'approved',
      already_applied: false,
      message: 'Membership request approved. The faculty account can now sign in.',
    })
    render(<StaffFacultyManager accessToken="jwt" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    await waitFor(() => expect(api.decideMembershipRequest).toHaveBeenCalledWith('jwt', request.request_id, 'approve'))
    expect(await screen.findByText('Membership request approved. The faculty account can now sign in.')).toBeDefined()
    expect(vi.mocked(api.listMembershipRequests).mock.calls.length).toBeGreaterThan(1)
  })

  it('does not show pending invitations in the roster', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({
      members: [
        {
          user_id: '20000000-0000-0000-0000-000000000001',
          name: '',
          email: 'xy faculty@example.test',
          role: 'faculty',
          status: 'active',
          created_at: null,
          updated_at: null,
        },
      ],
      total: 1,
    })
    render(<StaffFacultyManager accessToken="jwt" />)
    expect(await screen.findByText('xy faculty@example.test')).toBeDefined()
    expect(screen.queryByText('Invitation')).toBeNull()
    expect(screen.queryByRole('cell', { name: 'Pending' })).toBeNull()
    expect(screen.queryByRole('button', { name: /resend invitation/i })).toBeNull()
  })

  it.each(['staff', 'faculty'] as const)('retries sign-in setup for an approved %s account', async (role) => {
    vi.mocked(api.listMembershipRequests).mockResolvedValue({
      requests: [{ ...request, requested_role: role, status: 'approved' }],
      total: 1,
    })
    vi.mocked(api.decideMembershipRequest).mockResolvedValue({
      request_id: request.request_id,
      status: 'approved',
      already_applied: true,
      message: 'Membership request is already approved.',
    })
    render(<StaffFacultyManager accessToken="jwt" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Retry sign-in setup' }))
    await waitFor(() => expect(api.decideMembershipRequest).toHaveBeenCalledWith('jwt', request.request_id, 'approve'))
    expect(await screen.findByText('Sign-in setup completed. This account can now sign in.')).toBeDefined()
    expect(screen.queryByRole('button', { name: 'Reject' })).toBeNull()
  })

  it('reloads a committed approval after confirmation fails and keeps recovery available', async () => {
    vi.mocked(api.decideMembershipRequest).mockRejectedValue(new Error('Sign-in confirmation failed.'))
    vi.mocked(api.listMembershipRequests)
      .mockResolvedValueOnce({ requests: [request], total: 1 })
      .mockResolvedValue({ requests: [{ ...request, status: 'approved' }], total: 1 })
    render(<StaffFacultyManager accessToken="jwt" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Sign-in confirmation failed.')
    expect(await screen.findByRole('button', { name: 'Retry sign-in setup' })).toBeEnabled()
    expect(screen.queryByText('Sign-in setup completed. This account can now sign in.')).toBeNull()
  })

  it('does not retry sign-in setup for rejected requests', async () => {
    vi.mocked(api.listMembershipRequests).mockResolvedValue({
      requests: [{ ...request, status: 'rejected' }],
      total: 1,
    })
    render(<StaffFacultyManager accessToken="jwt" />)
    await screen.findByText('Ada Faculty')
    expect(screen.queryByRole('button', { name: 'Retry sign-in setup' })).toBeNull()
  })

  it('discards a pending approval result when the session changes', async () => {
    let finish: (value: Awaited<ReturnType<typeof api.decideMembershipRequest>>) => void = () => {}
    vi.mocked(api.decideMembershipRequest).mockReturnValue(
      new Promise((resolve) => {
        finish = resolve
      }),
    )
    const { rerender } = render(<StaffFacultyManager accessToken="old-session" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    vi.mocked(api.listMembershipRequests).mockResolvedValue({ requests: [], total: 0 })
    rerender(<StaffFacultyManager accessToken="new-session" />)
    await act(async () => {
      finish({ request_id: request.request_id, status: 'approved', already_applied: false, message: 'Old approval' })
    })
    expect(screen.queryByText('Old approval')).toBeNull()
    expect(screen.queryByText('Ada Faculty')).toBeNull()
  })

  it('reloads the current filter when an earlier approval finishes', async () => {
    let finish: (value: Awaited<ReturnType<typeof api.decideMembershipRequest>>) => void = () => {}
    vi.mocked(api.decideMembershipRequest).mockReturnValue(
      new Promise((resolve) => {
        finish = resolve
      }),
    )
    render(<StaffFacultyManager accessToken="jwt" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    fireEvent.click(screen.getByRole('tab', { name: 'Staff' }))
    await act(async () => {
      finish({ request_id: request.request_id, status: 'approved', already_applied: false, message: 'Approved' })
    })
    expect(api.listMembershipRequests).toHaveBeenLastCalledWith('jwt', 'staff', undefined)
  })
})
