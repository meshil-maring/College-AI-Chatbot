import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from './StaffFacultyManager.tsx'
import * as api from '../../services/adminApi.ts'

vi.mock('../../services/adminApi.ts', () => ({
  listMembershipRequests: vi.fn(),
  listMembershipRoster: vi.fn(),
  decideMembershipRequest: vi.fn(),
  changeMembershipStatus: vi.fn(),
  resendMembershipInvitation: vi.fn(),
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
      invitation_status: 'invited',
      message: 'Membership request approved and invitation queued.',
    })
    render(<StaffFacultyManager accessToken="jwt" />)
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    await waitFor(() => expect(api.decideMembershipRequest).toHaveBeenCalledWith('jwt', request.request_id, 'approve'))
    expect(await screen.findByText('Membership request approved and invitation queued.')).toBeDefined()
    expect(vi.mocked(api.listMembershipRequests).mock.calls.length).toBeGreaterThan(1)
  })
})
