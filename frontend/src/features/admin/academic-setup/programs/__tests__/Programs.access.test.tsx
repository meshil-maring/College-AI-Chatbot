import {
  api,
  auth,
  catalogue,
  program,
  renderPrograms,
  setCatalogue,
  Workspace,
  openCreate,
  fillProgram,
} from './Programs.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AdminApiError } from '../../../../../services/admin/http.ts'
import type { DegreeProgram } from '../../../../../types/academicSetup.ts'

describe('Program access and identity boundaries', () => {
  it('renders without requesting catalogues when the account has no read grant', () => {
    auth.user.effective_permissions = []
    renderPrograms()
    expect(screen.getByText(/does not have academic catalogue access/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add Program', exact: true })).toBeDisabled()
    expect(api.getAcademicSetup).not.toHaveBeenCalled()
  })

  it('allows read-only details while disabling writes', async () => {
    catalogue.records.programs = [program]
    catalogue.manageable = []
    renderPrograms()
    fireEvent.click(await screen.findByRole('button', { name: `View ${program.name}` }))
    const drawer = screen.getByRole('dialog', { name: 'Program details' })
    expect(within(drawer).getByRole('button', { name: 'Edit Program' })).toBeDisabled()
    expect(api.updateAcademicRecord).not.toHaveBeenCalled()
  })

  it('does not offer creation without a readable active institution department', async () => {
    catalogue.records.departments = []
    renderPrograms()
    await waitFor(() =>
      expect(screen.getByRole('region', { name: 'Program summary' })).toHaveAttribute('aria-busy', 'false'),
    )
    expect(screen.getByRole('button', { name: 'Add Program', exact: true })).toBeDisabled()
    expect(screen.getByText(/active department is required/)).toBeInTheDocument()
  })

  it('keeps department counts unavailable when the catalogue omits them', async () => {
    delete catalogue.records.departments
    catalogue.records.programs = [program]
    renderPrograms()
    await screen.findByRole('button', { name: `View ${program.name}` })
    expect(
      within(screen.getByRole('region', { name: 'Program summary' })).getByText('Departments').parentElement,
    ).toHaveTextContent('—Unavailable')
    expect(screen.getByRole('button', { name: 'Add Program', exact: true })).toBeDisabled()
  })

  it('hides denied data and recovers after Retry', async () => {
    vi.mocked(api.getAcademicSetup).mockRejectedValueOnce(new AdminApiError(403, 'Denied'))
    renderPrograms()
    expect(await screen.findByRole('heading', { name: 'Program access is unavailable' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => expect(screen.getAllByRole('button', { name: 'Add Program', exact: true })[0]).toBeEnabled())
  })

  it('rejects a top-level tenant mismatch', async () => {
    catalogue.institution_id = 'foreign'
    catalogue.records.programs = [program]
    renderPrograms()
    expect(await screen.findByRole('alert')).toHaveTextContent('unavailable for this institution')
    expect(screen.queryByRole('button', { name: `View ${program.name}` })).not.toBeInTheDocument()
  })

  it('labels a failed refresh as stale and disables mutations until recovery', async () => {
    catalogue.records.programs = [program]
    const view = renderPrograms()
    await screen.findByRole('button', { name: `Edit ${program.name}` })
    vi.mocked(api.getAcademicSetup).mockRejectedValueOnce(new Error('Offline'))
    const { queryClient } = await import('../../../../../lib/queryClient.ts')
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: ['admin', 'academic-overview'] })
    })
    expect(await screen.findByRole('alert')).toHaveTextContent('last loaded records')
    expect(screen.getByRole('button', { name: `Edit ${program.name}` })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => expect(screen.getByRole('button', { name: `Edit ${program.name}` })).toBeEnabled())
    view.unmount()
  })

  it('ignores a pending mutation after the authenticated identity is replaced', async () => {
    let resolve!: (value: DegreeProgram) => void
    vi.mocked(api.createAcademicRecord).mockImplementationOnce(
      () =>
        new Promise<DegreeProgram>((done) => {
          resolve = done
        }),
    )
    const view = renderPrograms()
    await openCreate()
    fillProgram()
    fireEvent.click(screen.getByRole('button', { name: 'Create Program' }))
    await waitFor(() => expect(api.createAcademicRecord).toHaveBeenCalledTimes(1))
    auth.accessToken = 'new-token'
    auth.user.institution_id = 'new-institution'
    setCatalogue({ institution_id: 'new-institution', records: { programs: [], departments: [] }, manageable: [] })
    view.rerender(<Workspace />)
    await screen.findByRole('heading', { name: 'No programs yet' })
    const reads = vi.mocked(api.getAcademicSetup).mock.calls.length
    await act(async () => resolve({ ...program, name: 'Old identity program' }))
    expect(screen.queryByText('Program created successfully.')).not.toBeInTheDocument()
    expect(screen.queryByText('Old identity program')).not.toBeInTheDocument()
    expect(api.getAcademicSetup).toHaveBeenCalledTimes(reads)
  })
})
