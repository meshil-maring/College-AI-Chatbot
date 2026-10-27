import {
  api,
  auth,
  catalogue,
  department,
  openCreate,
  fillDepartment,
  renderDepartments,
  Workspace,
  setCatalogue,
} from './Departments.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AdminApiError } from '../../../../../services/admin/http.ts'
import type { Department } from '../../../../../types/academicSetup.ts'

describe('Department access and session boundaries', () => {
  it('does not request catalogues or show sample records without academic read access', () => {
    auth.user.effective_permissions = []
    renderDepartments()
    expect(api.getAcademicSetup).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Add Department', exact: true })).toBeDisabled()
    const metrics = screen.getByRole('region', { name: 'Department summary' })
    expect(within(metrics).getAllByText('Not connected')).toHaveLength(3)
    expect(within(metrics).queryByText('0')).not.toBeInTheDocument()
    expect(screen.queryByText(department.name)).not.toBeInTheDocument()
  })

  it('allows read-only viewing and disables creation and editing for an inactive record', async () => {
    catalogue.manageable = []
    catalogue.records.departments![0].is_active = false
    renderDepartments()
    const view = await screen.findByRole('button', { name: `View ${department.name}` })
    expect(screen.getByRole('button', { name: `Edit ${department.name}` })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Add Department', exact: true })).toBeDisabled()
    fireEvent.click(view)
    const details = screen.getByRole('dialog', { name: 'Department details' })
    expect(within(details).getByText('Inactive')).toBeInTheDocument()
    expect(within(details).getByRole('button', { name: 'Edit Department' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: /reactivate|delete/i })).not.toBeInTheDocument()
  })

  it('rejects a mismatched institution envelope without exposing records or mutations', async () => {
    catalogue.institution_id = 'foreign'
    renderDepartments()
    expect(await screen.findByRole('alert')).toHaveTextContent('unavailable for this institution')
    expect(screen.queryByText(department.name)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add Department', exact: true })).toBeDisabled()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })

  it('shows a recoverable load error and distinguishes permission denial', async () => {
    vi.mocked(api.getAcademicSetup).mockRejectedValueOnce(new Error('Network unavailable'))
    renderDepartments()
    expect(await screen.findByText('Departments could not be loaded')).toBeInTheDocument()
    expect(screen.queryByText('No departments yet')).not.toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: 'Retry', exact: true })[0])
    expect(await screen.findByRole('button', { name: `View ${department.name}` })).toBeInTheDocument()
  })

  it('does not expose records after a denied read request', async () => {
    vi.mocked(api.getAcademicSetup).mockRejectedValueOnce(new AdminApiError(403, 'Permission denied'))
    renderDepartments()
    expect(await screen.findByText('Department access is unavailable')).toBeInTheDocument()
    expect(screen.queryByText(department.name)).not.toBeInTheDocument()
    expect(within(screen.getByRole('region', { name: 'Department summary' })).getAllByText('—')).toHaveLength(3)
  })

  it('discards drafts and ignores late saves after an identity change', async () => {
    let resolve!: (value: Department) => void
    vi.mocked(api.createAcademicRecord).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    const page = renderDepartments()
    await openCreate()
    fillDepartment()
    fireEvent.click(screen.getByRole('button', { name: 'Create Department', exact: true }))
    await waitFor(() => expect(api.createAcademicRecord).toHaveBeenCalledTimes(1))
    auth.accessToken = 'replacement-token'
    auth.user.institution_id = 'replacement-institution'
    setCatalogue({ institution_id: 'replacement-institution', records: { departments: [] }, manageable: [] })
    page.rerender(<Workspace />)
    expect(await screen.findByText('No departments yet')).toBeInTheDocument()
    const requests = vi.mocked(api.getAcademicSetup).mock.calls.length
    await act(async () => resolve({ ...department, department_id: 'late-department', name: 'Applied Sciences' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.queryByText('Department created successfully.')).not.toBeInTheDocument()
    expect(screen.queryByText('Applied Sciences')).not.toBeInTheDocument()
    expect(api.getAcademicSetup).toHaveBeenCalledTimes(requests)
  })

  it('opens the department quick action directly in the new drawer without submitting', async () => {
    renderDepartments('overview')
    await openCreate()
    expect(screen.getByRole('heading', { name: 'Departments', level: 1 })).toBeInTheDocument()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel', exact: true }))
    fireEvent.click(
      within(screen.getByRole('navigation', { name: 'Academic Setup navigation' })).getByRole('button', {
        name: 'Overview',
        exact: true,
      }),
    )
    fireEvent.click(
      within(screen.getByRole('navigation', { name: 'Academic Setup navigation' })).getByRole('button', {
        name: 'Departments',
        exact: true,
      }),
    )
    await screen.findByRole('button', { name: `View ${department.name}` })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
