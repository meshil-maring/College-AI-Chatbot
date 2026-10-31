import {
  api,
  auth,
  renderPlan,
  selectPlan,
  structureCatalogue,
  StudyPlanWorkspace,
} from '../../semester-plan/__tests__/StudyPlan.support.tsx'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'

it('edits shared names and codes without changing the semester number, ID or any assignments', async () => {
  const before = structuredClone(structureCatalogue.records)
  renderPlan()
  await selectPlan()
  const trigger = screen.getByRole('button', { name: 'Semester settings for Semester 1' })
  trigger.focus()
  fireEvent.click(trigger)
  const dialog = screen.getByRole('dialog', { name: 'Edit Program Semester' })
  const drawer = within(dialog)
  expect(drawer.getByText(/Changes affect all its curricula and classes/)).toBeInTheDocument()
  expect(drawer.queryByRole('combobox', { name: 'Program' })).not.toBeInTheDocument()
  expect(drawer.queryByRole('spinbutton', { name: 'Semester Number' })).not.toBeInTheDocument()
  expect(drawer.getByRole('textbox', { name: 'Semester Name' })).toHaveFocus()
  fireEvent.change(drawer.getByRole('textbox', { name: 'Semester Name' }), { target: { value: 'Foundation semester' } })
  fireEvent.change(drawer.getByRole('textbox', { name: 'Semester Code' }), { target: { value: 'FOUND' } })
  fireEvent.click(drawer.getByRole('button', { name: 'Save Changes' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  expect(api.updateStructureRecord).toHaveBeenCalledExactlyOnceWith('token-1', 'program_semesters', 'stage-1', {
    name: 'Foundation semester',
    code: 'FOUND',
  })
  expect(structureCatalogue.records.program_semesters![0]).toEqual({
    ...before.program_semesters![0],
    name: 'Foundation semester',
    code: 'FOUND',
  })
  expect(structureCatalogue.records.curriculum_subjects).toEqual(before.curriculum_subjects)
  expect(structureCatalogue.records.academic_sections).toEqual(before.academic_sections)
  expect(trigger).toHaveFocus()
})

it('confirms activating an existing inactive semester and reuses its ID for subjects', async () => {
  structureCatalogue.records.program_semesters![1].is_active = false
  renderPlan()
  await selectPlan()
  expect(screen.getByRole('button', { name: 'Add subject to Semester 2' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Semester settings for Semester 2' }))
  fireEvent.click(screen.getByRole('checkbox', { name: 'Active' }))
  fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))
  expect(screen.getByRole('alertdialog')).toHaveTextContent('affects every curriculum and class')
  expect(api.updateStructureRecord).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Confirm Change' }))
  await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument())
  expect(api.updateStructureRecord).toHaveBeenCalledExactlyOnceWith('token-1', 'program_semesters', 'stage-2', {
    is_active: true,
  })
  expect(screen.getByRole('button', { name: 'Add subject to Semester 2' })).toBeEnabled()
  expect(api.createStructureRecord).not.toHaveBeenCalled()
})

it('blocks publication while semester settings are open and confirms discarding changes', async () => {
  renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Semester settings for Semester 1' }))
  expect(screen.getByRole('button', { name: 'Review and publish' })).toBeDisabled()
  fireEvent.change(screen.getByRole('textbox', { name: 'Semester Code' }), { target: { value: 'UNSAVED' } })
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
  expect(screen.getByRole('alertdialog', { name: 'Discard your changes?' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Keep Editing' }))
  expect(screen.getByRole('textbox', { name: 'Semester Code' })).toHaveValue('UNSAVED')
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
  fireEvent.click(screen.getByRole('button', { name: 'Discard Changes' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Review and publish' })).toBeEnabled())
  expect(api.updateStructureRecord).not.toHaveBeenCalled()
})

const session = auth as typeof auth & { sessionGeneration?: number }
afterEach(() => {
  delete session.sessionGeneration
})
it('retains a settings draft during token renewal and discards it when the session changes', async () => {
  session.sessionGeneration = 1
  const view = renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Semester settings for Semester 1' }))
  fireEvent.change(screen.getByRole('textbox', { name: 'Semester Name' }), { target: { value: 'Unsaved foundation' } })
  auth.accessToken = 'renewed-token'
  view.rerender(<StudyPlanWorkspace />)
  expect(screen.getByRole('textbox', { name: 'Semester Name' })).toHaveValue('Unsaved foundation')
  session.sessionGeneration = 2
  view.rerender(<StudyPlanWorkspace />)
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})
