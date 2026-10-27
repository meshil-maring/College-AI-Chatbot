import {
  api,
  auth,
  baseApi,
  cohort,
  fillBatch,
  openAdd,
  renderBatches,
  structureCatalogue,
  Workspace,
} from './Batches.support.tsx'
import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AdminApiError } from '../../../../../services/admin/http.ts'

describe('Batch access and persistence', () => {
  it('makes no requests or sample records available without catalogue grants', () => {
    auth.user.effective_permissions = []
    renderBatches()
    expect(screen.getByRole('button', { name: 'Add Batch' })).toBeDisabled()
    expect(screen.queryByText('CSE 2026')).not.toBeInTheDocument()
    expect(api.getAcademicStructure).not.toHaveBeenCalled()
    expect(baseApi.getAcademicSetup).not.toHaveBeenCalled()
  })
  it('blocks writes for read-only access and hides denied data', async () => {
    structureCatalogue.manageable = []
    renderBatches()
    await screen.findByRole('button', { name: 'View CSE 2026' })
    expect(screen.getByRole('button', { name: 'Edit CSE 2026' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Add Batch' })).toBeDisabled()
  })
  it('offers Retry for schema errors without falling back to samples', async () => {
    vi.mocked(api.getAcademicStructure).mockRejectedValueOnce(new AdminApiError(503, 'Academic schema unavailable'))
    renderBatches()
    expect(await screen.findByRole('alert')).toHaveTextContent('Academic schema unavailable')
    expect(screen.queryByText('CSE 2026')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await screen.findByRole('button', { name: 'View CSE 2026' })
  })
  it('ignores a late save after identity replacement', async () => {
    let resolve!: (value: typeof cohort) => void
    vi.mocked(api.createStructureRecord).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    const view = renderBatches()
    await openAdd()
    fillBatch()
    fireEvent.click(screen.getByRole('button', { name: 'Create Batch' }))
    await waitFor(() => expect(api.createStructureRecord).toHaveBeenCalledTimes(1))
    auth.accessToken = 'new-token'
    auth.user.institution_id = 'new-institution'
    structureCatalogue.institution_id = 'new-institution'
    structureCatalogue.records.admission_cohorts = []
    view.rerender(<Workspace />)
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await waitFor(() => expect(api.getAcademicStructure).toHaveBeenCalledTimes(2))
    const reads = vi.mocked(api.getAcademicStructure).mock.calls.length
    await act(async () => resolve(cohort))
    expect(api.getAcademicStructure).toHaveBeenCalledTimes(reads)
    expect(screen.queryByText(/created successfully/)).not.toBeInTheDocument()
  })
})
