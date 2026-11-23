import './__tests__/StaffFacultyManager.support.ts'
import { CSE, member, request } from './__tests__/StaffFacultyManager.support.ts'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from './StaffFacultyManager.tsx'
import * as api from '../../../services/admin/adminApi.ts'

/** Pending requests can only be approved after the administrator picks a department. */
async function chooseDepartment() {
  fireEvent.change(await screen.findByRole('combobox', { name: 'Department for Ada Faculty' }), {
    target: { value: CSE.department_id },
  })
}

describe('StaffFacultyManager', () => {
  it('shows tenant-safe requests and the empty roster state', async () => {
    render(<StaffFacultyManager accessToken="jwt" />)
    expect(await screen.findByText('Ada Faculty')).toBeDefined()
    // The roster is its own page.
    expect(screen.queryByText('No staff or faculty are on the roster yet.')).toBeNull()
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    expect(await screen.findByText('No staff or faculty are on the roster yet.')).toBeDefined()
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
    await chooseDepartment()
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    await waitFor(() =>
      expect(api.decideMembershipRequest).toHaveBeenCalledWith(
        'jwt',
        request.request_id,
        'approve',
        CSE.department_id,
        'faculty',
      ),
    )
    expect(await screen.findByText('Membership request approved. The faculty account can now sign in.')).toBeDefined()
    expect(vi.mocked(api.listMembershipRequests).mock.calls.length).toBeGreaterThan(1)
  })

  it('does not show pending invitations in the roster', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({
      members: [member({ name: '', email: 'xy faculty@example.test', role: 'faculty' })],
      total: 1,
    })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
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
    await waitFor(() =>
      expect(api.decideMembershipRequest).toHaveBeenCalledWith(
        'jwt',
        request.request_id,
        'approve',
        undefined,
        undefined,
      ),
    )
    expect(await screen.findByText('Sign-in setup completed')).toBeDefined()
    expect(screen.getByText('This account can now sign in.')).toBeDefined()
    expect(screen.queryByRole('button', { name: 'Reject' })).toBeNull()
  })

  it('reloads a committed approval after confirmation fails and keeps recovery available', async () => {
    vi.mocked(api.decideMembershipRequest).mockRejectedValue(new Error('Sign-in confirmation failed.'))
    vi.mocked(api.listMembershipRequests)
      .mockResolvedValueOnce({ requests: [request], total: 1 })
      .mockResolvedValue({ requests: [{ ...request, status: 'approved' }], total: 1 })
    render(<StaffFacultyManager accessToken="jwt" />)
    await chooseDepartment()
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Sign-in confirmation failed.')
    expect(await screen.findByRole('button', { name: 'Retry sign-in setup' })).toBeEnabled()
    expect(screen.queryByText('Sign-in setup completed')).toBeNull()
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
    await chooseDepartment()
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
    await chooseDepartment()
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    fireEvent.click(screen.getByRole('tab', { name: 'Staff' }))
    const staffReads = () =>
      vi.mocked(api.listMembershipRequests).mock.calls.filter((call) => call[1] === 'staff').length
    await waitFor(() => expect(staffReads()).toBe(1))
    await act(async () => {
      finish({ request_id: request.request_id, status: 'approved', already_applied: false, message: 'Approved' })
    })
    // The open Staff filter is reloaded (the summary's pending count refreshes too).
    await waitFor(() => expect(staffReads()).toBe(2))
  })

  it('shows saved requests at once when returning to the page, without requesting again', async () => {
    const first = render(<StaffFacultyManager accessToken="jwt" />)
    expect(await screen.findByText('Ada Faculty')).toBeDefined()
    await waitFor(() => expect(api.listMembershipRoster).toHaveBeenCalled())
    await waitFor(() => expect(api.listMembershipInvitations).toHaveBeenCalled())
    const calls = [api.listMembershipRequests, api.listMembershipRoster, api.listMembershipInvitations].map(
      (read) => vi.mocked(read).mock.calls.length,
    )
    first.unmount()
    render(<StaffFacultyManager accessToken="jwt" />)
    expect(screen.getByText('Ada Faculty')).toBeDefined()
    expect(screen.queryByText('Loading membership requests…')).toBeNull()
    // Returning to the page makes no new requests while the data is fresh.
    expect(
      [api.listMembershipRequests, api.listMembershipRoster, api.listMembershipInvitations].map(
        (read) => vi.mocked(read).mock.calls.length,
      ),
    ).toEqual(calls)
  })

  it('never reuses saved data for a different session', async () => {
    const first = render(<StaffFacultyManager accessToken="jwt" />)
    expect(await screen.findByText('Ada Faculty')).toBeDefined()
    first.unmount()
    vi.mocked(api.listMembershipRequests).mockResolvedValue({ requests: [], total: 0 })
    render(<StaffFacultyManager accessToken="other-session" />)
    expect(screen.queryByText('Ada Faculty')).toBeNull()
    await waitFor(() =>
      expect(api.listMembershipRequests).toHaveBeenLastCalledWith('other-session', undefined, 'pending'),
    )
  })
})
