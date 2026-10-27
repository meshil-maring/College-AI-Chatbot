import {
  api,
  auth,
  catalogue,
  year,
  renderCalendar,
  openCreate,
  fillYear,
  Workspace,
  setCatalogue,
} from './Calendar.support.tsx'
import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AdminApiError } from '../../../../../services/admin/http.ts'
import type { AcademicYear } from '../../../../../types/academicSetup.ts'

describe('Calendar access and session boundaries', () => {
  it('does not request catalogues without read access', () => {
    auth.user.effective_permissions = []
    renderCalendar()
    expect(screen.getByRole('button', { name: 'Add Academic Year', exact: true })).toBeDisabled()
    expect(screen.getByText(/does not have academic catalogue access/)).toBeInTheDocument()
    expect(api.getAcademicSetup).not.toHaveBeenCalled()
  })

  it('allows viewing but disables editing for read-only access', async () => {
    catalogue.manageable = []
    renderCalendar()
    fireEvent.click(await screen.findByRole('button', { name: `View ${year.name}` }, { timeout: 5000 }))
    expect(screen.getByRole('dialog', { name: 'Academic Year details' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit Academic Year', exact: true })).toBeDisabled()
    expect(screen.getByLabelText(/Academic Year Name/)).toBeDisabled()
  })

  it('creates only the year without semester management access', async () => {
    catalogue.manageable = ['academic_years']
    renderCalendar()
    await openCreate()
    fillYear()
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Create Academic Year' }))
    await screen.findByText('Academic year created successfully.')
    expect(api.createAcademicRecord).toHaveBeenCalledTimes(1)
  })

  it('labels stale data and disables writes until a refresh succeeds', async () => {
    renderCalendar()
    await screen.findByRole('article', { name: year.name })
    vi.mocked(api.getAcademicSetup).mockRejectedValueOnce(new Error('Offline'))
    const { queryClient } = await import('../../../../../lib/queryClient.ts')
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: ['admin', 'academic-overview'] })
    })
    expect(await screen.findByRole('alert')).toHaveTextContent('last loaded records')
    expect(screen.getByRole('button', { name: 'Add Academic Year', exact: true })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Add Academic Year', exact: true })).toBeEnabled())
  })

  it('hides records on denied reads and rejects mismatched tenant responses', async () => {
    vi.mocked(api.getAcademicSetup).mockRejectedValueOnce(new AdminApiError(403, 'Denied'))
    const view = renderCalendar()
    await screen.findByRole('alert')
    expect(screen.queryByRole('article', { name: year.name })).not.toBeInTheDocument()
    view.unmount()
    catalogue.institution_id = 'foreign'
    renderCalendar()
    expect(await screen.findByRole('alert')).toHaveTextContent('unavailable for this institution')
    expect(screen.queryByRole('article', { name: year.name })).not.toBeInTheDocument()
  })

  it('stops a multi-request save after the authenticated identity is replaced', async () => {
    let resolve!: (value: AcademicYear) => void
    vi.mocked(api.createAcademicRecord).mockImplementationOnce(
      () =>
        new Promise<AcademicYear>((done) => {
          resolve = done
        }) as never,
    )
    const view = renderCalendar()
    await openCreate()
    fillYear()
    fireEvent.click(screen.getByRole('button', { name: 'Create Academic Year' }))
    await waitFor(() => expect(api.createAcademicRecord).toHaveBeenCalledTimes(1))
    const calls = vi.mocked(api.getAcademicSetup).mock.calls.length
    auth.accessToken = 'replacement-token'
    auth.user.institution_id = 'replacement-institution'
    auth.user.effective_permissions = []
    setCatalogue({ institution_id: 'replacement-institution', records: {}, manageable: [] })
    view.rerender(<Workspace />)
    await act(async () => resolve({ ...year, academic_year_id: 'old-save' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(api.createAcademicRecord).toHaveBeenCalledTimes(1)
    expect(api.getAcademicSetup).toHaveBeenCalledTimes(calls)
    expect(screen.queryByText('Academic year created successfully.')).not.toBeInTheDocument()
  })
})
