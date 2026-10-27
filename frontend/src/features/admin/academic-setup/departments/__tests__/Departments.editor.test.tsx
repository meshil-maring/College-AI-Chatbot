import { api, department, fillDepartment, openCreate, renderDepartments } from './Departments.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AdminApiError } from '../../../../../services/admin/http.ts'
import type { Department } from '../../../../../types/academicSetup.ts'

describe('Department drawers', () => {
  it('restores the invoking control after an unchanged drawer is closed', async () => {
    renderDepartments()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Add Department', exact: true })).toBeEnabled())
    const trigger = screen.getByRole('button', { name: 'Add Department', exact: true })
    trigger.focus()
    await openCreate()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel', exact: true }))
    expect(trigger).toHaveFocus()
  })

  it('requires an explicit status and displays inline errors without submitting', async () => {
    renderDepartments()
    await openCreate()
    expect(screen.getByRole('radio', { name: /^Active/ })).not.toBeChecked()
    expect(screen.getByRole('radio', { name: /^Inactive/ })).not.toBeChecked()
    fireEvent.click(screen.getByRole('button', { name: 'Create Department', exact: true }))
    expect(screen.getByText('Enter a department name.')).toBeInTheDocument()
    expect(screen.getByText('Enter a department code.')).toBeInTheDocument()
    expect(screen.getByText('Choose a department status.')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /Department Name/ })).toHaveFocus()
    fireEvent.change(screen.getByRole('textbox', { name: /Department Name/ }), { target: { value: 'Applied' } })
    expect(screen.getByRole('textbox', { name: /Department Name/ })).toHaveFocus()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })

  it('submits trimmed values through the existing institution-scoped service', async () => {
    renderDepartments()
    await openCreate()
    fillDepartment(' Applied Sciences ')
    fireEvent.change(screen.getByRole('textbox', { name: /Description/ }), {
      target: { value: ' Interdisciplinary study ' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Create Department', exact: true }))
    await screen.findByText('Department created successfully.')
    expect(api.createAcademicRecord).toHaveBeenCalledWith('token-1', 'departments', {
      name: 'Applied Sciences',
      code: 'AS',
      description: 'Interdisciplinary study',
      is_active: true,
    })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(await screen.findByRole('row', { name: /Applied Sciences/ })).toBeInTheDocument()
  })

  it('keeps entries after duplicate-code rejection and focuses the code field', async () => {
    vi.mocked(api.createAcademicRecord).mockRejectedValueOnce(
      new AdminApiError(409, 'Duplicate', undefined, 'ACADEMIC_DUPLICATE'),
    )
    renderDepartments()
    await openCreate()
    fillDepartment('Applied Sciences', 'CSE')
    fireEvent.click(screen.getByRole('button', { name: 'Create Department', exact: true }))
    await screen.findByText('This department code is already in use in your institution.')
    expect(screen.getByRole('textbox', { name: /Department Name/ })).toHaveValue('Applied Sciences')
    expect(screen.getByRole('textbox', { name: /Department Code/ })).toHaveFocus()
    expect(screen.getByRole('radio', { name: /^Active/ })).toBeChecked()
    fireEvent.change(screen.getByRole('textbox', { name: /Department Code/ }), { target: { value: 'AS' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create Department', exact: true }))
    expect(await screen.findByText('Department created successfully.')).toBeInTheDocument()
  })

  it('retains a failed request and disables repeat submission while saving', async () => {
    let reject!: (value: unknown) => void
    vi.mocked(api.createAcademicRecord).mockImplementationOnce(
      () =>
        new Promise<Department>((_done, fail) => {
          reject = fail
        }),
    )
    renderDepartments()
    await openCreate()
    fillDepartment()
    fireEvent.click(screen.getByRole('button', { name: 'Create Department', exact: true }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled())
    expect(screen.getByRole('textbox', { name: /Department Name/ })).toBeDisabled()
    expect(api.createAcademicRecord).toHaveBeenCalledTimes(1)
    await act(async () => reject(new Error('Service unavailable.')))
    expect(await screen.findByRole('alert')).toHaveTextContent('Service unavailable.')
    expect(screen.getByRole('textbox', { name: /Department Name/ })).toHaveValue('Applied Sciences')
    expect(screen.getByRole('button', { name: 'Create Department', exact: true })).toBeEnabled()
  })

  it('confirms discarding unsaved edits and preserves them when editing continues', async () => {
    renderDepartments()
    await openCreate()
    fillDepartment()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel', exact: true }))
    const confirm = screen.getByRole('alertdialog', { name: 'Discard your changes?' })
    expect(within(confirm).getByText('Applied Sciences')).toBeInTheDocument()
    expect(within(confirm).getByRole('button', { name: 'Keep Editing' })).toHaveFocus()
    fireEvent.click(within(confirm).getByRole('button', { name: 'Keep Editing' }))
    expect(screen.getByRole('textbox', { name: /Department Name/ })).toHaveValue('Applied Sciences')
    fireEvent.click(screen.getByRole('button', { name: 'Cancel', exact: true }))
    fireEvent.click(screen.getByRole('button', { name: 'Discard Changes' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })

  it('populates edits and confirms status changes before calling the existing update', async () => {
    renderDepartments()
    fireEvent.click(await screen.findByRole('button', { name: `Edit ${department.name}` }))
    expect(screen.getByRole('textbox', { name: /Department Name/ })).toHaveValue(department.name)
    fireEvent.click(screen.getByRole('radio', { name: /^Inactive/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))
    expect(screen.getByRole('alertdialog', { name: 'Confirm status change' })).toHaveTextContent(
      'Active dependencies may prevent this change.',
    )
    expect(api.updateAcademicRecord).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Changes' }))
    await screen.findByText('Department updated successfully.')
    expect(api.updateAcademicRecord).toHaveBeenCalledWith(
      'token-1',
      'departments',
      department.department_id,
      expect.objectContaining({ is_active: false }),
    )
  })
})
