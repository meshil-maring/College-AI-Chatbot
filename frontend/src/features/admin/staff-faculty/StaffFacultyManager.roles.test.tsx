import './__tests__/StaffFacultyManager.support.ts'
import { CSE, member, request } from './__tests__/StaffFacultyManager.support.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from './StaffFacultyManager.tsx'
import * as api from '../../../services/admin/adminApi.ts'

describe('Staff and Faculty Management — roles', () => {
  it('starts each request at the role the applicant asked for and offers only Staff or Faculty', async () => {
    render(<StaffFacultyManager accessToken="jwt" />)
    const role = await screen.findByRole('combobox', { name: 'Role for Ada Faculty' })
    expect(role).toHaveValue('faculty')
    expect(
      within(role)
        .getAllByRole('option')
        .map((option) => option.textContent),
    ).toEqual(['Faculty (Teacher)', 'Staff'])
  })

  it('approves an applicant as the role the administrator chose', async () => {
    vi.mocked(api.decideMembershipRequest).mockResolvedValue({
      request_id: request.request_id,
      status: 'approved',
      already_applied: false,
      message: 'Membership request approved. The staff account can now sign in.',
    })
    render(<StaffFacultyManager accessToken="jwt" />)
    fireEvent.change(await screen.findByRole('combobox', { name: 'Role for Ada Faculty' }), {
      target: { value: 'staff' },
    })
    fireEvent.change(screen.getByRole('combobox', { name: 'Department for Ada Faculty' }), {
      target: { value: CSE.department_id },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    await waitFor(() =>
      expect(api.decideMembershipRequest).toHaveBeenCalledWith(
        'jwt',
        request.request_id,
        'approve',
        CSE.department_id,
        'staff',
      ),
    )
    expect(window.confirm).toHaveBeenCalledWith('Approve Ada Faculty as Staff?')
  })

  it('switches a roster member between Staff and Faculty', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [member({ role: 'faculty' })], total: 1 })
    vi.mocked(api.setMemberRole).mockResolvedValue({
      user_id: member().user_id,
      role: 'staff',
      already_applied: false,
      message: 'Role changed to Staff. They will see the new workspace after signing in again.',
    })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    const role = await screen.findByRole('combobox', { name: 'Role for Sam Staff' })
    expect(role).toHaveValue('faculty')
    fireEvent.change(role, { target: { value: 'staff' } })
    await waitFor(() => expect(api.setMemberRole).toHaveBeenCalledWith('jwt', member().user_id, 'staff'))
    expect(await screen.findByText(/Role changed to Staff/)).toBeInTheDocument()
  })

  it('shows why the server refused a role change', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [member({ role: 'faculty' })], total: 1 })
    vi.mocked(api.setMemberRole).mockRejectedValue(
      new Error('This member is a Head of Department. End that appointment before making them Staff.'),
    )
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    fireEvent.change(await screen.findByRole('combobox', { name: 'Role for Sam Staff' }), {
      target: { value: 'staff' },
    })
    expect(await screen.findByRole('alert')).toHaveTextContent('Head of Department')
  })

  it('does not change the role when the administrator cancels', async () => {
    vi.mocked(window.confirm).mockReturnValue(false)
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [member()], total: 1 })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    fireEvent.change(await screen.findByRole('combobox', { name: 'Role for Sam Staff' }), {
      target: { value: 'faculty' },
    })
    expect(api.setMemberRole).not.toHaveBeenCalled()
  })
})
