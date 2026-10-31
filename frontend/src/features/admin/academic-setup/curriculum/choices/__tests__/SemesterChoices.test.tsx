import {
  api,
  fillChoices,
  openChoices,
  registrationCatalogue,
  renderPlan,
  savedGroup,
  selectPlan,
  semesterChoices,
  structureCatalogue,
} from './SemesterChoices.support.tsx'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { expect, it } from 'vitest'

it('creates complete alternatives in the selected semester and excludes compulsory subjects', async () => {
  renderPlan()
  await selectPlan()
  const form = openChoices()
  expect(form.queryByRole('combobox')).not.toBeInTheDocument()
  expect(form.queryByRole('checkbox', { name: 'Data Mining' })).not.toBeInTheDocument()
  fireEvent.change(form.getByRole('textbox', { name: 'Group Name' }), { target: { value: 'Science choices' } })
  fireEvent.click(form.getByRole('button', { name: 'Save choice group' }))
  expect(form.getByRole('alert')).toHaveTextContent('Select at least one subject for Option 1.')
  expect(api.saveChoiceGroup).not.toHaveBeenCalled()
  for (const checkbox of form.getAllByRole('checkbox', { name: 'DBMS' })) fireEvent.click(checkbox)
  fireEvent.click(form.getByRole('button', { name: 'Save choice group' }))
  await waitFor(() => expect(screen.queryByRole('form', { name: 'Subject choice group' })).not.toBeInTheDocument())
  expect(api.saveChoiceGroup).toHaveBeenCalledExactlyOnceWith(
    'token-1',
    {
      curriculum_version_id: 'version-1',
      program_semester_id: 'stage-1',
      name: 'Science choices',
      options: [
        { name: 'Option 1', curriculum_subject_ids: ['optional-mapping'] },
        { name: 'Option 2', curriculum_subject_ids: ['optional-mapping'] },
      ],
    },
    undefined,
  )
  expect(semesterChoices().getByRole('heading', { name: 'Science choices' })).toBeInTheDocument()
  expect(semesterChoices(2).queryByText('Science choices')).not.toBeInTheDocument()
})

it('retains a group draft while adding an optional subject above it', async () => {
  structureCatalogue.records.curriculum_subjects = []
  renderPlan()
  await selectPlan()
  let form = openChoices()
  fireEvent.change(form.getByRole('textbox', { name: 'Group Name' }), { target: { value: 'My semester choices' } })
  fireEvent.change(form.getAllByRole('textbox', { name: 'Option Name' })[1], { target: { value: 'Database and labs' } })
  expect(form.getByRole('status')).toHaveTextContent('Add subjects to this semester first')
  fireEvent.click(screen.getByRole('button', { name: 'Add subject to Semester 1' }))
  const drawer = within(screen.getByRole('dialog', { name: 'Add subject in Semester 1' }))
  fireEvent.change(drawer.getByRole('combobox', { name: 'Subject', exact: true }), {
    target: { value: 'optional-course' },
  })
  fireEvent.click(drawer.getByRole('checkbox', { name: 'Every student must take this subject' }))
  fireEvent.click(drawer.getByRole('button', { name: 'Add subject', exact: true }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  form = within(screen.getByRole('form', { name: 'Subject choice group' }))
  expect(form.getByRole('textbox', { name: 'Group Name' })).toHaveValue('My semester choices')
  expect(form.getAllByRole('textbox', { name: 'Option Name' })[1]).toHaveValue('Database and labs')
  expect(form.getAllByRole('checkbox', { name: 'DBMS' })).toHaveLength(2)
})

it('updates selectable choices after editing a compulsory subject in place', async () => {
  structureCatalogue.records.curriculum_subjects!.forEach((subject) => {
    subject.is_required = true
  })
  renderPlan()
  await selectPlan()
  const form = openChoices()
  expect(form.getByRole('status')).toHaveTextContent('All subjects in this semester are compulsory')
  fireEvent.change(form.getByRole('textbox', { name: 'Group Name' }), { target: { value: 'Keep this draft' } })
  fireEvent.click(screen.getByRole('button', { name: 'Edit Data Mining in Semester 1' }))
  fireEvent.click(screen.getByRole('checkbox', { name: 'Every student must take this subject' }))
  fireEvent.click(screen.getByRole('button', { name: 'Save subject' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  expect(form.getByRole('textbox', { name: 'Group Name' })).toHaveValue('Keep this draft')
  expect(form.getAllByRole('checkbox', { name: 'Data Mining' })).toHaveLength(2)
  expect(form.getByText(/Compulsory subjects:/)).toHaveTextContent('DBMS')
})

it('edits and deletes the correct draft group with a confirmation', async () => {
  registrationCatalogue.groups = [structuredClone(savedGroup)]
  renderPlan()
  await selectPlan()
  fireEvent.click(semesterChoices().getByRole('button', { name: 'Edit Science choices' }))
  const form = within(screen.getByRole('form', { name: 'Subject choice group' }))
  fireEvent.change(form.getByRole('textbox', { name: 'Group Name' }), { target: { value: 'Updated choices' } })
  fireEvent.click(form.getByRole('button', { name: 'Save choice group' }))
  await waitFor(() => expect(screen.queryByRole('form', { name: 'Subject choice group' })).not.toBeInTheDocument())
  expect(api.saveChoiceGroup).toHaveBeenCalledWith(
    'token-1',
    expect.objectContaining({
      name: 'Updated choices',
      curriculum_version_id: 'version-1',
      program_semester_id: 'stage-1',
    }),
    'saved-group',
  )
  fireEvent.click(semesterChoices().getByRole('button', { name: 'Delete Updated choices' }))
  expect(api.deleteChoiceGroup).not.toHaveBeenCalled()
  fireEvent.click(semesterChoices().getByRole('button', { name: 'Confirm delete' }))
  await waitFor(() =>
    expect(semesterChoices().queryByRole('heading', { name: 'Updated choices' })).not.toBeInTheDocument(),
  )
  expect(api.deleteChoiceGroup).toHaveBeenCalledExactlyOnceWith('token-1', 'saved-group')
})

it('keeps groups scoped to their own curriculum, semester and institution', async () => {
  registrationCatalogue.groups = [
    structuredClone(savedGroup),
    {
      ...savedGroup,
      choice_group_id: 'other-version',
      curriculum_version_id: 'version-2',
      name: 'Other curriculum choices',
    },
    {
      ...savedGroup,
      choice_group_id: 'other-semester',
      program_semester_id: 'stage-2',
      name: 'Second semester choices',
    },
    { ...savedGroup, choice_group_id: 'other-tenant', institution_id: 'other', name: 'Private choices' },
  ]
  renderPlan()
  await selectPlan()
  expect(semesterChoices().getByRole('heading', { name: 'Science choices' })).toBeInTheDocument()
  expect(semesterChoices().queryByText('Second semester choices')).not.toBeInTheDocument()
  expect(semesterChoices(2).getByRole('heading', { name: 'Second semester choices' })).toBeInTheDocument()
  expect(screen.queryByText('Other curriculum choices')).not.toBeInTheDocument()
  expect(screen.queryByText('Private choices')).not.toBeInTheDocument()
})

it('includes saved choice alternatives in the publication review', async () => {
  registrationCatalogue.groups = [structuredClone(savedGroup)]
  renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Review and publish' }))
  const review = within(screen.getByRole('alertdialog', { name: 'Review study plan' }))
  expect(review.getByText('Science choices — choose one option')).toBeInTheDocument()
  expect(review.getByText('Database studies: DBMS')).toBeInTheDocument()
  expect(review.getByText('Database and labs: DBMS')).toBeInTheDocument()
  expect(api.saveChoiceGroup).not.toHaveBeenCalled()
})
