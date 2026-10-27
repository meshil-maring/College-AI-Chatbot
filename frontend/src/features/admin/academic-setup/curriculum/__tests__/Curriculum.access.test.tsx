import {
  api,
  auth,
  catalogue,
  course,
  link,
  Workspace,
  chooseSubject,
  openMapping,
  renderCurriculum,
  setCatalogue,
  loaded,
} from './Curriculum.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AdminApiError } from '../../../../../services/admin/http.ts'
import type { ProgramCourse } from '../../../../../types/academicSetup.ts'

describe('Curriculum access and identity boundaries', () => {
  it('does not request catalogues without read grants and exposes no creation controls', () => {
    auth.user.effective_permissions = []
    renderCurriculum()
    expect(screen.getByText(/does not have academic catalogue access/)).toBeInTheDocument()
    expect(api.getAcademicSetup).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Add Curriculum', exact: true })).not.toBeInTheDocument()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
  })

  it('shows read-only mappings and disables every mutation control', async () => {
    catalogue.manageable = []
    renderCurriculum()
    await loaded()
    expect(screen.getByRole('row', { name: /Data Mining/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: `Edit mapping for ${course.name}` })).toBeDisabled()
    expect(screen.getByRole('button', { name: `Deactivate mapping for ${course.name}` })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Add Subject', exact: true })).toBeDisabled()
    expect(api.updateAcademicRecord).not.toHaveBeenCalled()
  })

  it('shows unavailable counts for missing mappings and disables creation without active parents', async () => {
    delete catalogue.records.program_courses
    renderCurriculum()
    await loaded()
    expect(
      within(screen.getByRole('region', { name: 'Curriculum summary' })).getByText('Programs').parentElement,
    ).toHaveTextContent('—')
    expect(screen.getByText('Subject mappings are unavailable for this account.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add Subject', exact: true })).not.toBeInTheDocument()
  })

  it('rejects a top-level institution mismatch without exposing records', async () => {
    catalogue.institution_id = 'foreign'
    renderCurriculum()
    expect(await screen.findByRole('alert', {}, { timeout: 5000 })).toHaveTextContent(
      'unavailable for this institution',
    )
    expect(screen.queryByRole('row', { name: /Data Mining/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /B.Tech CSE/ })).not.toBeInTheDocument()
  })

  it('hides denied records and recovers after retry', async () => {
    vi.mocked(api.getAcademicSetup).mockRejectedValueOnce(new AdminApiError(403, 'Denied'))
    renderCurriculum()
    expect(
      await screen.findByRole('heading', { name: 'Curriculum access is unavailable' }, { timeout: 5000 }),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => expect(screen.getByRole('button', { name: `Edit mapping for ${course.name}` })).toBeEnabled(), {
      timeout: 5000,
    })
  })

  it('marks a failed refresh stale and blocks writes until recovery', async () => {
    renderCurriculum()
    await loaded()
    vi.mocked(api.getAcademicSetup).mockRejectedValueOnce(new Error('Offline'))
    const { queryClient } = await import('../../../../../lib/queryClient.ts')
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: ['admin', 'academic-overview'] })
    })
    expect(await screen.findByRole('alert')).toHaveTextContent('last loaded records')
    expect(screen.getByRole('row', { name: /Data Mining/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: `Edit mapping for ${course.name}` })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await waitFor(() => expect(screen.getByRole('button', { name: `Edit mapping for ${course.name}` })).toBeEnabled(), {
      timeout: 5000,
    })
  })

  it('ignores late mapping results after identity replacement', async () => {
    let resolve!: (value: ProgramCourse) => void
    vi.mocked(api.createAcademicRecord).mockImplementationOnce(
      () =>
        new Promise<ProgramCourse>((done) => {
          resolve = done
        }),
    )
    const view = renderCurriculum()
    const drawer = await openMapping()
    chooseSubject()
    fireEvent.click(drawer.getByRole('button', { name: 'Add Subject', exact: true }))
    await waitFor(() => expect(api.createAcademicRecord).toHaveBeenCalledTimes(1))
    auth.accessToken = 'new-token'
    auth.user.institution_id = 'new-institution'
    setCatalogue({
      institution_id: 'new-institution',
      records: { programs: [], program_courses: [], courses: [], departments: [] },
      manageable: [],
    })
    view.rerender(<Workspace />)
    await screen.findByRole('heading', { name: 'No programs yet' }, { timeout: 5000 })
    const reads = vi.mocked(api.getAcademicSetup).mock.calls.length
    await act(async () => resolve(link))
    expect(screen.queryByText('Subject mapped successfully.')).not.toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(api.getAcademicSetup).toHaveBeenCalledTimes(reads)
  })
})
