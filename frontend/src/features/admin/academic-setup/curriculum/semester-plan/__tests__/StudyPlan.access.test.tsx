import {
  api,
  auth,
  catalogue,
  renderPlan,
  selectPlan,
  structureCatalogue,
  StudyPlanWorkspace,
} from './StudyPlan.support.tsx'
import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

const session = auth as typeof auth & { sessionGeneration?: number }
afterEach(() => {
  delete session.sessionGeneration
})

it.each(['department', 'program', 'year', 'version', 'semester'])(
  'blocks writes when the selected %s is inactive',
  async (parent) => {
    if (parent === 'department') catalogue.records.departments![0].is_active = false
    if (parent === 'program') catalogue.records.programs![0].is_active = false
    if (parent === 'year') catalogue.records.academic_years![0].is_active = false
    if (parent === 'version') structureCatalogue.records.curriculum_versions![0].is_active = false
    if (parent === 'semester') structureCatalogue.records.program_semesters![0].is_active = false
    renderPlan()
    await selectPlan()
    expect(screen.getByRole('button', { name: 'Add subject to Semester 1' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Edit Data Mining in Semester 1' })).toBeDisabled()
    if (parent !== 'semester') expect(screen.getByRole('button', { name: 'Review and publish' })).toBeDisabled()
    expect(api.createStructureRecord).not.toHaveBeenCalled()
  },
)

it('guides an empty catalogue back to draft creation', async () => {
  structureCatalogue.records.curriculum_versions = []
  renderPlan()
  fireEvent.click(await screen.findByRole('button', { name: 'Go to curriculum list' }))
  expect(screen.getByRole('button', { name: 'Add Curriculum' })).toBeInTheDocument()
  expect(api.createStructureRecord).not.toHaveBeenCalled()
})

it('hides a mismatched institution response', async () => {
  vi.mocked(api.getAcademicStructure).mockResolvedValue({ ...structureCatalogue, institution_id: 'foreign-tenant' })
  renderPlan()
  await screen.findByRole('alert')
  expect(screen.queryByRole('combobox', { name: 'Choose a curriculum' })).not.toBeInTheDocument()
  expect(screen.queryByText('CSE Curriculum')).not.toBeInTheDocument()
})

it('keeps a subject draft during token renewal in the same session', async () => {
  session.sessionGeneration = 101
  const view = renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Add subject to Semester 2' }))
  fireEvent.change(screen.getByRole('combobox', { name: 'Subject', exact: true }), { target: { value: 'english' } })
  auth.accessToken = 'renewed-token'
  view.rerender(<StudyPlanWorkspace />)
  expect(screen.getByRole('combobox', { name: 'Subject', exact: true })).toHaveValue('english')
})

it.each(['session', 'permissions', 'institution'])('clears subject drafts when the %s changes', async (change) => {
  session.sessionGeneration = 101
  const view = renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Add subject to Semester 2' }))
  fireEvent.change(screen.getByRole('combobox', { name: 'Subject', exact: true }), { target: { value: 'english' } })
  if (change === 'session') session.sessionGeneration = 102
  if (change === 'permissions') auth.user.effective_permissions = []
  if (change === 'institution') auth.user.institution_id = 'other'
  view.rerender(<StudyPlanWorkspace />)
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(api.createStructureRecord).not.toHaveBeenCalled()
})
