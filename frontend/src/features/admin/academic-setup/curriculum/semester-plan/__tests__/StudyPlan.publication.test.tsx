import { api, renderPlan, selectPlan, structureCatalogue } from './StudyPlan.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { expect, it, vi } from 'vitest'

it('reviews actual semester subjects and publishes only after explicit confirmation', async () => {
  renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Review and publish' }))
  const review = within(screen.getByRole('alertdialog', { name: 'Review study plan' }))
  expect(review.getByText('Data Mining · Compulsory')).toBeInTheDocument()
  expect(review.getByText('No subjects included. Check whether this is intended.')).toBeInTheDocument()
  expect(review.getByText(/1 set-up semester is empty and 0 are not set up/)).toBeInTheDocument()
  expect(api.updateStructureRecord).not.toHaveBeenCalled()
  fireEvent.click(review.getByRole('button', { name: 'Publish study plan' }))
  await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument())
  expect(api.updateStructureRecord).toHaveBeenCalledExactlyOnceWith('token-1', 'curriculum_versions', 'version-1', {
    status: 'published',
  })
  expect(screen.getByText('Study plan published. You can now assign it to a batch.')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Add subject/ })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Assign to a batch' }))
  await screen.findByRole('heading', { name: 'Batches', level: 1 })
})

it('explains the next step for student choices without making subjects compulsory', async () => {
  structureCatalogue.records.curriculum_subjects![0].is_required = false
  renderPlan()
  await selectPlan()
  expect(
    within(screen.getByRole('region', { name: 'Student choices in Semester 1' })).getByRole('button', {
      name: 'Add choice group',
    }),
  ).toBeInTheDocument()
  expect(screen.getByRole('region', { name: 'Semester 1 subjects' })).toHaveTextContent('Student choice')
  expect(api.updateStructureRecord).not.toHaveBeenCalled()
})

it('requires an included subject and an active draft before publication', async () => {
  structureCatalogue.records.curriculum_subjects![0].is_active = false
  renderPlan()
  await selectPlan()
  expect(screen.getByText('Add at least one subject before publishing.')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Review and publish' })).toBeDisabled()
})

it('shows server publication validation and retains the review for correction', async () => {
  vi.mocked(api.updateStructureRecord).mockRejectedValue(new Error('Each choice group needs at least two options'))
  renderPlan()
  await selectPlan()
  screen.getByRole('button', { name: 'Review and publish' }).focus()
  fireEvent.click(screen.getByRole('button', { name: 'Review and publish' }))
  fireEvent.click(screen.getByRole('button', { name: 'Publish study plan' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Each choice group needs at least two options')
  expect(screen.getByRole('alertdialog')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Keep editing' }))
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Review and publish' })).toHaveFocus()
})

it('rejects an unverifiable publication response', async () => {
  vi.mocked(api.updateStructureRecord).mockResolvedValue({
    ...structureCatalogue.records.curriculum_versions![0],
    institution_id: 'other-tenant',
  })
  renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Review and publish' }))
  fireEvent.click(screen.getByRole('button', { name: 'Publish study plan' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be verified for this institution')
  expect(screen.queryByText(/Study plan published\./)).not.toBeInTheDocument()
})

it('locks publication while pending and does not refresh or notify after unmount', async () => {
  let resolve!: (value: never) => void
  vi.mocked(api.updateStructureRecord).mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done
      }),
  )
  const view = renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Review and publish' }))
  const publish = screen.getByRole('button', { name: 'Publish study plan' })
  fireEvent.click(publish)
  fireEvent.click(publish)
  expect(api.updateStructureRecord).toHaveBeenCalledOnce()
  expect(screen.getByRole('button', { name: 'Publishing…' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Keep editing' })).toBeDisabled()
  const reads = vi.mocked(api.getAcademicStructure).mock.calls.length
  view.unmount()
  await act(async () =>
    resolve({ ...structureCatalogue.records.curriculum_versions![0], status: 'published' } as never),
  )
  expect(api.getAcademicStructure).toHaveBeenCalledTimes(reads)
})

it('distinguishes missing subject data from an empty study plan', async () => {
  delete structureCatalogue.records.curriculum_subjects
  renderPlan()
  fireEvent.change(await screen.findByRole('combobox', { name: 'Choose a curriculum' }), {
    target: { value: 'version-1' },
  })
  expect(screen.getByText(/Semester or subject records are unavailable/)).toBeInTheDocument()
  expect(screen.queryByRole('region', { name: 'Semester 1 subjects' })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Review and publish' })).not.toBeInTheDocument()
})
