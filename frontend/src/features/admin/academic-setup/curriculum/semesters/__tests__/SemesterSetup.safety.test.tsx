import {
  api,
  auth,
  renderPlan,
  selectPlan,
  structureCatalogue,
  StudyPlanWorkspace,
} from '../../semester-plan/__tests__/StudyPlan.support.tsx'
import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'

it('blocks repeated setup and publication while semesters are being created', async () => {
  structureCatalogue.records.program_semesters!.pop()
  const save = vi.mocked(api.createStructureRecord).getMockImplementation()!
  let finish!: () => void
  vi.mocked(api.createStructureRecord).mockImplementationOnce(
    (...args) =>
      new Promise((resolve) => {
        finish = async () => resolve(await save(...args))
      }),
  )
  renderPlan()
  await selectPlan()
  const trigger = screen.getByRole('button', { name: 'Set up 1 missing semester' })
  fireEvent.click(trigger)
  await waitFor(() => expect(api.createStructureRecord).toHaveBeenCalledOnce())
  fireEvent.click(trigger)
  expect(screen.getByRole('button', { name: 'Setting up semesters…' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Review and publish' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Add subject to Semester 1' })).toBeDisabled()
  expect(screen.getByRole('combobox', { name: 'Choose a curriculum' })).toBeDisabled()
  await act(async () => finish())
  await waitFor(() => expect(screen.getByRole('button', { name: 'Add subject to Semester 2' })).toBeEnabled())
  expect(api.createStructureRecord).toHaveBeenCalledOnce()
})

it.each(['foreign catalogue', 'foreign stage', 'published version', 'revoked grant'] as const)(
  'rejects %s during server recheck',
  async (change) => {
    structureCatalogue.records.program_semesters!.pop()
    renderPlan()
    await selectPlan()
    const snapshot = structuredClone(structureCatalogue)
    if (change === 'foreign catalogue') snapshot.institution_id = 'other'
    if (change === 'foreign stage') {
      vi.mocked(api.createStructureRecord).mockResolvedValueOnce({
        ...snapshot.records.program_semesters![0],
        institution_id: 'other',
        semester_number: 2,
      })
    }
    if (change === 'published version') snapshot.records.curriculum_versions![0].status = 'published'
    if (change === 'revoked grant') snapshot.manageable = []
    vi.mocked(api.getAcademicStructure).mockResolvedValueOnce(snapshot)
    fireEvent.click(screen.getByRole('button', { name: 'Set up 1 missing semester' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      change === 'foreign stage' ? 'could not be verified' : 'setup is unavailable',
    )
    if (change !== 'foreign stage') expect(api.createStructureRecord).not.toHaveBeenCalled()
    expect(
      screen.queryByText('Semesters are ready. Existing semester records have been reused.'),
    ).not.toBeInTheDocument()
  },
)

it('stops the creation queue after unmount and ignores a late save', async () => {
  structureCatalogue.records.program_semesters = []
  const save = vi.mocked(api.createStructureRecord).getMockImplementation()!
  let finish!: () => void
  vi.mocked(api.createStructureRecord).mockImplementationOnce(
    (...args) =>
      new Promise((resolve) => {
        finish = async () => resolve(await save(...args))
      }),
  )
  const view = renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Set up 2 missing semesters' }))
  await waitFor(() => expect(api.createStructureRecord).toHaveBeenCalledOnce())
  const reads = vi.mocked(api.getAcademicStructure).mock.calls.length
  view.unmount()
  await act(async () => finish())
  expect(api.createStructureRecord).toHaveBeenCalledOnce()
  expect(api.getAcademicStructure).toHaveBeenCalledTimes(reads)
})

it('stops setup if another session replaces the administrator while reading', async () => {
  structureCatalogue.records.program_semesters = []
  const view = renderPlan()
  await selectPlan()
  let finish!: (value: typeof structureCatalogue) => void
  vi.mocked(api.getAcademicStructure).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve
      }),
  )
  fireEvent.click(screen.getByRole('button', { name: 'Set up 2 missing semesters' }))
  await waitFor(() => expect(finish).toBeDefined())
  auth.accessToken = 'replacement-login'
  view.rerender(<StudyPlanWorkspace />)
  await act(async () => finish(structuredClone(structureCatalogue)))
  expect(api.createStructureRecord).not.toHaveBeenCalled()
})
