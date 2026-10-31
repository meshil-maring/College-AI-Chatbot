import {
  api,
  auth,
  fillChoices,
  openChoices,
  registrationCatalogue,
  renderPlan,
  savedGroup,
  selectPlan,
  semesterChoices,
  structureCatalogue,
  StudyPlanWorkspace,
} from './SemesterChoices.support.tsx'
import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'

it('hides choice editing when the server denies management', async () => {
  registrationCatalogue.can_manage_choices = false
  registrationCatalogue.groups = [structuredClone(savedGroup)]
  renderPlan()
  await selectPlan()
  expect(semesterChoices().getByText('Read-only access to student choices.')).toBeInTheDocument()
  expect(semesterChoices().queryByRole('button')).not.toBeInTheDocument()
  expect(semesterChoices().getByRole('heading', { name: 'Science choices' })).toBeInTheDocument()
})

it.each(['published', 'archived'] as const)('shows %s choice groups without mutation actions', async (status) => {
  structureCatalogue.records.curriculum_versions![0].status = status
  registrationCatalogue.groups = [structuredClone(savedGroup)]
  renderPlan()
  await selectPlan()
  expect(semesterChoices().getByRole('heading', { name: 'Science choices' })).toBeInTheDocument()
  expect(semesterChoices().queryByRole('button')).not.toBeInTheDocument()
})

it('retains failed entries and rejects another institution in the save response', async () => {
  vi.mocked(api.saveChoiceGroup).mockResolvedValue({ institution_id: 'foreign', choice_group_id: 'group-1' })
  renderPlan()
  await selectPlan()
  const form = openChoices()
  fillChoices(form)
  fireEvent.click(form.getByRole('button', { name: 'Save choice group' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('saved record could not be verified')
  expect(form.getByRole('textbox', { name: 'Group Name' })).toHaveValue('Science choices')
  expect(form.getAllByRole('checkbox', { name: 'DBMS' }).every((item) => (item as HTMLInputElement).checked)).toBe(true)
})

it('blocks duplicate group submissions and publication until saving finishes', async () => {
  let resolve!: (value: { institution_id: string; choice_group_id: string }) => void
  vi.mocked(api.saveChoiceGroup).mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done
      }),
  )
  renderPlan()
  await selectPlan()
  const form = openChoices()
  fillChoices(form)
  const formNode = form.getByRole('button', { name: 'Save choice group' }).closest('form')!
  fireEvent.submit(formNode)
  fireEvent.submit(formNode)
  await waitFor(() => expect(api.saveChoiceGroup).toHaveBeenCalledOnce())
  await form.findByRole('button', { name: 'Saving…' })
  expect(screen.getByRole('button', { name: 'Review and publish' })).toBeDisabled()
  expect(form.getByRole('button', { name: 'Cancel' })).toBeDisabled()
  await act(async () => resolve({ institution_id: 'institution-1', choice_group_id: 'group-1' }))
  await waitFor(() => expect(screen.queryByRole('form', { name: 'Subject choice group' })).not.toBeInTheDocument())
})

it('keeps saved subjects visible when choices fail to load and supports retry', async () => {
  vi.mocked(api.getRegistrationCatalogue).mockRejectedValueOnce(new Error('Choices service unavailable'))
  renderPlan()
  await selectPlan()
  expect(screen.getByRole('region', { name: 'Semester 1 subjects' })).toHaveTextContent('Data Mining')
  expect(screen.getByRole('button', { name: 'Review and publish' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Retry student choices' }))
  await waitFor(() => expect(semesterChoices().getByRole('button', { name: 'Add choice group' })).toBeEnabled())
  expect(screen.getByRole('button', { name: 'Review and publish' })).toBeEnabled()
})

it('clears choice drafts after an identity change and ignores late save callbacks', async () => {
  let resolve!: (value: { institution_id: string; choice_group_id: string }) => void
  vi.mocked(api.saveChoiceGroup).mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done
      }),
  )
  const view = renderPlan()
  await selectPlan()
  const form = openChoices()
  fillChoices(form)
  fireEvent.click(form.getByRole('button', { name: 'Save choice group' }))
  await waitFor(() => expect(api.saveChoiceGroup).toHaveBeenCalledOnce())
  auth.user.user_id = 'replacement-admin'
  view.rerender(<StudyPlanWorkspace />)
  expect(screen.queryByRole('form', { name: 'Subject choice group' })).not.toBeInTheDocument()
  await screen.findByRole('combobox', { name: 'Choose a curriculum' })
  const reads = vi.mocked(api.getRegistrationCatalogue).mock.calls.length
  await act(async () => resolve({ institution_id: 'institution-1', choice_group_id: 'group-1' }))
  expect(api.getRegistrationCatalogue).toHaveBeenCalledTimes(reads)
  expect(screen.queryByText('Saved successfully.')).not.toBeInTheDocument()
})

it('waits for every open choice draft to be saved or cancelled before publication', async () => {
  renderPlan()
  await selectPlan()
  const first = openChoices(1)
  const second = openChoices(2)
  expect(screen.getByRole('button', { name: 'Review and publish' })).toBeDisabled()
  expect(screen.getByText('Save or cancel the open choice group before publishing.')).toBeInTheDocument()
  fireEvent.click(first.getByRole('button', { name: 'Cancel' }))
  expect(screen.getByRole('button', { name: 'Review and publish' })).toBeDisabled()
  fireEvent.click(second.getByRole('button', { name: 'Cancel' }))
  expect(screen.getByRole('button', { name: 'Review and publish' })).toBeEnabled()
})
