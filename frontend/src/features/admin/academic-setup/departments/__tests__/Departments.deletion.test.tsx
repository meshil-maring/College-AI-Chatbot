import {
  api,
  auth,
  catalogue,
  department,
  program,
  renderDepartments,
  Workspace,
  setCatalogue,
} from './Departments.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AdminApiError } from '../../../../../services/admin/http.ts'
import type { Department } from '../../../../../types/academicSetup.ts'

async function openDeletion() {
  const trigger = await screen.findByRole('button', { name: `Delete ${department.name}` })
  trigger.focus()
  fireEvent.click(trigger)
  return screen.findByRole('alertdialog', { name: 'Delete department?' })
}

describe('Department deletion', () => {
  it('requires explicit confirmation, focuses Cancel and restores focus on cancellation', async () => {
    renderDepartments()
    const dialog = await openDeletion()
    expect(within(dialog).getByText(/cannot be undone/)).toBeInTheDocument()
    const cancel = within(dialog).getByRole('button', { name: 'Cancel' })
    expect(cancel).toHaveFocus()
    expect(api.deleteDepartment).not.toHaveBeenCalled()
    fireEvent.click(cancel)
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: `Delete ${department.name}` })).toHaveFocus()
    expect(api.deleteDepartment).not.toHaveBeenCalled()
  })

  it('deletes once, blocks repeat actions while pending and refreshes the list and totals', async () => {
    let resolve!: (value: Department) => void
    vi.mocked(api.deleteDepartment).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    renderDepartments()
    const dialog = await openDeletion()
    const confirm = within(dialog).getByRole('button', { name: 'Delete Department' })
    fireEvent.click(confirm)
    fireEvent.click(confirm)
    await waitFor(() => expect(api.deleteDepartment).toHaveBeenCalledTimes(1))
    expect(api.deleteDepartment).toHaveBeenCalledWith('token-1', department.department_id)
    expect(within(dialog).getByRole('button', { name: 'Deleting…' })).toBeDisabled()
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toBeDisabled()
    fireEvent(dialog, new Event('cancel', { cancelable: true }))
    expect(dialog).toBeInTheDocument()
    catalogue.records.departments = []
    await act(async () => resolve(department))
    expect(await screen.findByText('Department deleted successfully.')).toBeInTheDocument()
    expect(await screen.findByText('No departments yet')).toBeInTheDocument()
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Departments', level: 1 })).toHaveFocus()
    expect(api.getAcademicSetup).toHaveBeenCalledTimes(2)
  })

  it.each([true, false])('blocks departments with linked programs even when active is %s', async (active) => {
    catalogue.records.programs = [{ ...program, is_active: active }]
    renderDepartments()
    const dialog = await openDeletion()
    expect(within(dialog).getByRole('alert')).toHaveTextContent('linked programs, including inactive records')
    expect(within(dialog).getByRole('button', { name: 'Delete Department' })).toBeDisabled()
    expect(api.deleteDepartment).not.toHaveBeenCalled()
  })

  it('blocks an inactive subject even when the department has no programs', async () => {
    catalogue.records.courses = [
      {
        course_id: 'course-1',
        institution_id: department.institution_id,
        department_id: department.department_id,
        name: 'Programming',
        code: 'CS101',
        description: null,
        is_active: false,
        credits: 3,
        lecture_hours: null,
        tutorial_hours: null,
        practical_hours: null,
      },
    ]
    renderDepartments()
    const dialog = await openDeletion()
    expect(within(dialog).getByRole('alert')).toHaveTextContent('linked subjects')
    expect(within(dialog).getByRole('button', { name: 'Delete Department' })).toBeDisabled()
  })

  it('keeps the department and shows backend conflicts for links absent from the catalogue', async () => {
    vi.mocked(api.deleteDepartment).mockRejectedValueOnce(
      new AdminApiError(
        409,
        'This department cannot be deleted because it has linked records, including inactive records.',
        undefined,
        'DEPARTMENT_IN_USE',
      ),
    )
    renderDepartments()
    const dialog = await openDeletion()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Department' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('linked records')
    expect(catalogue.records.departments).toHaveLength(1)
    expect(screen.queryByText('Department deleted successfully.')).not.toBeInTheDocument()
  })

  it('allows retry after failure and deletes an unused inactive department', async () => {
    catalogue.records.departments![0].is_active = false
    vi.mocked(api.deleteDepartment)
      .mockRejectedValueOnce(new Error('Network unavailable'))
      .mockImplementationOnce(async () => {
        catalogue.records.departments = []
        return { ...department, is_active: false }
      })
    renderDepartments()
    const dialog = await openDeletion()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Department' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Network unavailable')
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Department' }))
    expect(await screen.findByText('Department deleted successfully.')).toBeInTheDocument()
    expect(api.deleteDepartment).toHaveBeenCalledTimes(2)
  })

  it('does not offer deletion to read-only users', async () => {
    catalogue.manageable = []
    renderDepartments()
    await screen.findByRole('button', { name: `View ${department.name}` })
    expect(screen.queryByRole('button', { name: /^Delete/ })).not.toBeInTheDocument()
  })

  it('ignores late deletion success after the institution identity is replaced', async () => {
    let resolve!: (value: Department) => void
    vi.mocked(api.deleteDepartment).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    const page = renderDepartments()
    const dialog = await openDeletion()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Department' }))
    await waitFor(() => expect(api.deleteDepartment).toHaveBeenCalledTimes(1))
    auth.accessToken = 'replacement-token'
    auth.user.institution_id = 'replacement-institution'
    setCatalogue({ institution_id: 'replacement-institution', records: { departments: [] }, manageable: [] })
    page.rerender(<Workspace />)
    expect(await screen.findByText('No departments yet')).toBeInTheDocument()
    const requests = vi.mocked(api.getAcademicSetup).mock.calls.length
    await act(async () => resolve(department))
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(screen.queryByText('Department deleted successfully.')).not.toBeInTheDocument()
    expect(api.getAcademicSetup).toHaveBeenCalledTimes(requests)
  })

  it('rejects a response identifying a different institution', async () => {
    vi.mocked(api.deleteDepartment).mockResolvedValueOnce({ ...department, institution_id: 'foreign' })
    renderDepartments()
    const dialog = await openDeletion()
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete Department' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('could not be verified')
    expect(screen.queryByText('Department deleted successfully.')).not.toBeInTheDocument()
  })
})
