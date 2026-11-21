import { department, renderDepartments } from './Departments.support.tsx'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as transfers from '../../../../../services/students/transferApi.ts'

vi.mock('../../../../../services/students/transferApi.ts', () => ({
  getDepartmentHeads: vi.fn(),
  addDepartmentHead: vi.fn(),
  endDepartmentHead: vi.fn(),
}))

function head(userId: string, name: string) {
  return {
    department_id: department.department_id,
    faculty_user_id: userId,
    name,
    email: null,
    assigned_at: '2026-11-21T00:00:00Z',
    is_active_faculty: true,
  }
}

const faculty = [
  { user_id: 'f1', name: 'Asha Head', email: 'asha@x.test' },
  { user_id: 'f2', name: 'Ben Head', email: 'ben@x.test' },
  { user_id: 'f3', name: 'Cara New', email: 'cara@x.test' },
]

function change(facultyUserId: string) {
  return {
    department_id: department.department_id,
    faculty_user_id: facultyUserId,
    institution_id: 'institution-1',
    already_applied: false,
    head_ids: [],
  }
}

async function openPanel() {
  const row = await screen.findByRole('row', { name: /Computer Science and Engineering/ })
  fireEvent.click(within(row).getByRole('button', { name: /View/ }))
  const drawer = screen.getByRole('dialog', { name: 'Department details' })
  const panel = within(drawer).getByRole('region', { name: 'Head of Department' })
  await within(panel).findByRole('group', { name: 'Current Heads of Department' })
  return panel
}

describe('Departments — several Heads of Department', () => {
  beforeEach(() => {
    vi.mocked(transfers.getDepartmentHeads).mockResolvedValue({
      institution_id: 'institution-1',
      heads: [head('f1', 'Asha Head'), head('f2', 'Ben Head')],
      faculty,
    })
    vi.mocked(transfers.addDepartmentHead).mockImplementation(async (_token, _id, user) => change(user))
    vi.mocked(transfers.endDepartmentHead).mockImplementation(async (_token, _id, user) => change(user))
  })

  it('lists every current head and offers only other faculty to add', async () => {
    renderDepartments()
    const panel = await openPanel()
    expect(within(panel).getByText('Asha Head')).toBeInTheDocument()
    expect(within(panel).getByText('Ben Head')).toBeInTheDocument()
    const select = within(panel).getByRole('combobox', { name: 'Add a Head of Department' })
    expect(
      within(select)
        .getAllByRole('option')
        .map((option) => option.textContent),
    ).toEqual(['Choose a faculty member…', 'Cara New — cara@x.test'])
  })

  it('adds a co-head without replacing the others', async () => {
    renderDepartments()
    const panel = await openPanel()
    fireEvent.change(within(panel).getByRole('combobox', { name: 'Add a Head of Department' }), {
      target: { value: 'f3' },
    })
    fireEvent.click(within(panel).getByRole('button', { name: 'Add Head of Department' }))
    await waitFor(() =>
      expect(transfers.addDepartmentHead).toHaveBeenCalledWith('token-1', department.department_id, 'f3'),
    )
    expect(transfers.endDepartmentHead).not.toHaveBeenCalled()
  })

  it('removes one head and keeps the rest', async () => {
    renderDepartments()
    const panel = await openPanel()
    fireEvent.click(within(panel).getByRole('button', { name: 'Remove Ben Head as Head of Department' }))
    await waitFor(() =>
      expect(transfers.endDepartmentHead).toHaveBeenCalledWith('token-1', department.department_id, 'f2'),
    )
    expect(transfers.endDepartmentHead).toHaveBeenCalledTimes(1)
  })
})
