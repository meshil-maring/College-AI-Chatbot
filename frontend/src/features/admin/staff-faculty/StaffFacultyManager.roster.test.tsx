import './__tests__/StaffFacultyManager.support.ts'
import { chooseAction, CSE, member } from './__tests__/StaffFacultyManager.support.ts'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StaffFacultyManager from './StaffFacultyManager.tsx'
import * as api from '../../../services/admin/adminApi.ts'

const roster = [
  member({ user_id: 'u1', name: 'Zed Staff', email: 'zed@x.test' }),
  member({
    user_id: 'u2',
    name: 'Amy Faculty',
    email: 'amy@x.test',
    role: 'faculty',
    department_id: CSE.department_id,
  }),
  member({ user_id: 'u3', name: 'Old Faculty', email: 'old@x.test', role: 'faculty', status: 'deactivated' }),
]

function rowNames() {
  const table = screen.getByRole('table')
  return within(table)
    .getAllByRole('row')
    .slice(1)
    .map((row) => within(row).getAllByRole('cell')[0].querySelector('p')?.textContent)
}

describe('Staff and Faculty Management — roster search and summary', () => {
  it('summarises pending requests and the active roster', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: roster, total: 3 })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    const summary = await screen.findByRole('region', { name: 'Staff and faculty summary' })
    await screen.findByText('Zed Staff')
    const value = (label: string) => within(summary).getByText(label).nextElementSibling?.textContent
    expect(value('Awaiting approval')).toBe('1')
    expect(value('Active faculty (teachers)')).toBe('1')
    expect(value('Active staff')).toBe('1')
    expect(value('Without a department')).toBe('1')
  })

  it('lists members alphabetically and filters by search, role and status', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: roster, total: 3 })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    await screen.findByText('Zed Staff')
    expect(rowNames()).toEqual(['Amy Faculty', 'Old Faculty', 'Zed Staff'])

    fireEvent.change(screen.getByRole('searchbox', { name: 'Search staff and faculty' }), {
      target: { value: 'zed' },
    })
    expect(rowNames()).toEqual(['Zed Staff'])
    expect(screen.getByText(/Showing 1 of/)).toBeInTheDocument()

    fireEvent.click(screen.getAllByRole('button', { name: 'Clear filters' })[0])
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by role' }), { target: { value: 'faculty' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by status' }), { target: { value: 'active' } })
    expect(rowNames()).toEqual(['Amy Faculty'])
  })

  it('finds members without a department and offers to clear an empty result', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: roster, total: 3 })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    await screen.findByText('Zed Staff')
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by department' }), { target: { value: 'none' } })
    expect(rowNames()).toEqual(['Old Faculty', 'Zed Staff'])

    fireEvent.change(screen.getByRole('searchbox', { name: 'Search staff and faculty' }), {
      target: { value: 'nobody' },
    })
    expect(screen.getByText('No members match these filters.')).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: 'Clear filters' })[1])
    expect(rowNames()).toHaveLength(3)
  })

  it('lets the administrator dismiss a result message', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [roster[0]], total: 1 })
    vi.mocked(api.changeMembershipStatus).mockResolvedValue({ message: 'Member deactivated.' } as never)
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    await chooseAction('Zed Staff', 'Deactivate')
    expect(await screen.findByText('Member deactivated.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss message' }))
    expect(screen.queryByText('Member deactivated.')).toBeNull()
  })

  it('keeps every row action in one keyboard-friendly menu', async () => {
    vi.mocked(api.listMembershipRoster).mockResolvedValue({ members: [roster[1]], total: 1 })
    render(<StaffFacultyManager accessToken="jwt" defaultPage="roster" />)
    const button = await screen.findByRole('button', { name: 'Actions for Amy Faculty' })
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('button', { name: 'Deactivate' })).toBeNull()
    fireEvent.keyDown(button, { key: 'ArrowDown' })
    const menu = screen.getByRole('menu', { name: 'Actions for Amy Faculty' })
    const items = within(menu).getAllByRole('menuitem')
    expect(items.map((item) => item.textContent)).toEqual(['Manage HOD', 'Deactivate'])
    expect(items[0]).toHaveFocus()
    fireEvent.keyDown(menu, { key: 'ArrowDown' })
    expect(items[1]).toHaveFocus()
    fireEvent.keyDown(menu, { key: 'ArrowDown' })
    expect(items[0]).toHaveFocus()
    fireEvent.keyDown(menu, { key: 'Escape' })
    expect(screen.queryByRole('menu')).toBeNull()
    expect(button).toHaveFocus()
  })
})
