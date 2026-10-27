import { api, auth, baseApi, catalogue, structureCatalogue, renderSections, Workspace } from './Sections.support.tsx'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AdminApiError } from '../../../../../services/admin/http.ts'

describe('Section access boundaries', () => {
  it('has no sample fallback or requests without read grants', () => {
    auth.user.effective_permissions = []
    renderSections()
    expect(screen.getByRole('button', { name: 'Add Section' })).toBeDisabled()
    expect(screen.queryByText('CSE26A')).not.toBeInTheDocument()
    expect(api.getAcademicStructure).not.toHaveBeenCalled()
    expect(baseApi.getAcademicSetup).not.toHaveBeenCalled()
  })
  it('disables creation and edits for read-only grants', async () => {
    structureCatalogue.manageable = []
    renderSections()
    await screen.findByRole('button', { name: 'View Section A, CSE 2026' })
    expect(screen.getByRole('button', { name: 'Add Section' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Edit Section A, CSE 2026' })).toBeDisabled()
  })
  it('rejects mismatched tenant data and discards an open drawer after identity replacement', async () => {
    const view = renderSections()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Add Section' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Add Section' }))
    auth.accessToken = 'replacement'
    auth.user.institution_id = 'replacement-institution'
    view.rerender(<Workspace />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent('unavailable for this institution')
    expect(screen.queryByText('CSE26A')).not.toBeInTheDocument()
  })
  it('hides denied records and recovers through Retry', async () => {
    vi.mocked(api.getAcademicStructure).mockRejectedValueOnce(new AdminApiError(403, 'Denied'))
    renderSections()
    await screen.findByRole('alert')
    expect(screen.queryByText('CSE26A')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await screen.findByRole('button', { name: 'View Section A, CSE 2026' })
  })
  it('requires usable batch, program progression and term parents before enabling creation', async () => {
    catalogue.records.semesters = []
    renderSections()
    await screen.findByRole('button', { name: 'View Section A, CSE 2026' })
    expect(screen.getByRole('button', { name: 'Add Section' })).toBeDisabled()
  })
})
