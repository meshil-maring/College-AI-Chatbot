import {
  api,
  auth,
  catalogue,
  subject,
  renderSubjects,
  setCatalogue,
  Workspace,
  openCreate,
  fillSubject,
} from './Subjects.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AdminApiError } from '../../../../../services/admin/http.ts'
import type { Course } from '../../../../../types/academicSetup.ts'

describe('Subject access and identity boundaries', () => {
  it('renders without requesting catalogues when the account has no read grant', () => {
    auth.user.effective_permissions = []
    renderSubjects()
    expect(screen.getByText(/does not have academic catalogue access/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add Subject', exact: true })).toBeDisabled()
    expect(api.getAcademicSetup).not.toHaveBeenCalled()
  })

  it('allows read-only details while disabling writes', async () => {
    catalogue.records.courses = [subject]
    catalogue.manageable = []
    renderSubjects()
    fireEvent.click(await screen.findByRole('button', { name: `View ${subject.name}` }))
    const drawer = screen.getByRole('dialog', { name: 'Subject details' })
    expect(within(drawer).getByRole('button', { name: 'Edit Subject' })).toBeDisabled()
    expect(api.updateAcademicRecord).not.toHaveBeenCalled()
  })

  it('does not offer creation without a readable active institution department', async () => {
    catalogue.records.departments = []
    renderSubjects()
    await waitFor(() =>
      expect(screen.getByRole('region', { name: 'Subject summary' })).toHaveAttribute('aria-busy', 'false'),
    )
    expect(screen.getByRole('button', { name: 'Add Subject', exact: true })).toBeDisabled()
    expect(screen.getByText(/active department is required/)).toBeInTheDocument()
  })

  it('keeps department counts unavailable when the catalogue omits them', async () => {
    delete catalogue.records.departments
    catalogue.records.courses = [subject]
    renderSubjects()
    await screen.findByRole('button', { name: `View ${subject.name}` })
    expect(
      within(screen.getByRole('region', { name: 'Subject summary' })).getByText('Departments').parentElement,
    ).toHaveTextContent('—Unavailable')
    expect(screen.getByRole('button', { name: 'Add Subject', exact: true })).toBeDisabled()
  })

  it('hides denied data and recovers after Retry', async () => {
    vi.mocked(api.getAcademicSetup).mockRejectedValueOnce(new AdminApiError(403, 'Denied'))
    renderSubjects()
    expect(await screen.findByRole('heading', { name: 'Subject access is unavailable' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => expect(screen.getAllByRole('button', { name: 'Add Subject', exact: true })[0]).toBeEnabled())
  })

  it('rejects a top-level tenant mismatch', async () => {
    catalogue.institution_id = 'foreign'
    catalogue.records.courses = [subject]
    renderSubjects()
    expect(await screen.findByRole('alert')).toHaveTextContent('unavailable for this institution')
    expect(screen.queryByRole('button', { name: `View ${subject.name}` })).not.toBeInTheDocument()
  })

  it('labels a failed refresh as stale and disables mutations until recovery', async () => {
    catalogue.records.courses = [subject]
    const view = renderSubjects()
    await screen.findByRole('button', { name: `Edit ${subject.name}` })
    vi.mocked(api.getAcademicSetup).mockRejectedValueOnce(new Error('Offline'))
    const { queryClient } = await import('../../../../../lib/queryClient.ts')
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: ['admin', 'academic-overview'] })
    })
    expect(await screen.findByRole('alert')).toHaveTextContent('last loaded records')
    expect(screen.getByRole('button', { name: `Edit ${subject.name}` })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => expect(screen.getByRole('button', { name: `Edit ${subject.name}` })).toBeEnabled())
    view.unmount()
  })

  it('ignores a pending mutation after the authenticated identity is replaced', async () => {
    let resolve!: (value: Course) => void
    vi.mocked(api.createAcademicRecord).mockImplementationOnce(
      () =>
        new Promise<Course>((done) => {
          resolve = done
        }),
    )
    const view = renderSubjects()
    await openCreate()
    fillSubject()
    fireEvent.click(screen.getByRole('button', { name: 'Create Subject' }))
    await waitFor(() => expect(api.createAcademicRecord).toHaveBeenCalledTimes(1))
    auth.accessToken = 'new-token'
    auth.user.institution_id = 'new-institution'
    setCatalogue({ institution_id: 'new-institution', records: { courses: [], departments: [] }, manageable: [] })
    view.rerender(<Workspace />)
    await screen.findByRole('heading', { name: 'No subjects yet' })
    const reads = vi.mocked(api.getAcademicSetup).mock.calls.length
    await act(async () => resolve({ ...subject, name: 'Old identity subject' }))
    expect(screen.queryByText('Subject created successfully.')).not.toBeInTheDocument()
    expect(screen.queryByText('Old identity subject')).not.toBeInTheDocument()
    expect(api.getAcademicSetup).toHaveBeenCalledTimes(reads)
  })
})
