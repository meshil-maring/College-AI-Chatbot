import '../__tests__/StaffFacultyManager.support.ts'
import { chooseAction, member } from '../__tests__/StaffFacultyManager.support.ts'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from '../StaffFacultyManager.tsx'
import * as api from '../../../../services/admin/adminApi.ts'

describe('Account history', () => {
  it('shows who changed what, newest first', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [member({ user_id: 's-1' })], total: 1 })
    vi.mocked(api.getMemberHistory).mockResolvedValue({
      user_id: 's-1',
      entries: [
        {
          audit_id: 'h-2',
          action: 'member.role.change',
          label: 'Role changed',
          actor_name: 'Olive Owner',
          performed_at: '2026-11-22T10:00:00Z',
          details: { from: 'staff', to: 'faculty' },
        },
        {
          audit_id: 'h-1',
          action: 'staff_suspended',
          label: 'Suspended',
          actor_name: 'System',
          performed_at: '2026-11-21T10:00:00Z',
          details: { status: 'suspended' },
        },
      ],
    })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    await chooseAction('Sam Staff', 'History')
    const dialog = screen.getByRole('dialog', { name: 'Account history' })
    const list = await within(dialog).findByRole('list', { name: 'Changes' })
    const items = within(list).getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('Role changed')
    expect(items[0]).toHaveTextContent('staff → faculty')
    expect(items[0]).toHaveTextContent('by Olive Owner')
    expect(items[1]).toHaveTextContent('now suspended')
    expect(api.getMemberHistory).toHaveBeenCalledWith('jwt', 's-1')
  })

  it('says so when nothing has been recorded', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [member({ user_id: 's-1' })], total: 1 })
    vi.mocked(api.getMemberHistory).mockResolvedValue({ user_id: 's-1', entries: [] })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    await chooseAction('Sam Staff', 'History')
    expect(await screen.findByText('No recorded changes yet.')).toBeInTheDocument()
  })
})
