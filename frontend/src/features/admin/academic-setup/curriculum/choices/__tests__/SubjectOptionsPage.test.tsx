import '../../../__tests__/AcademicSetup.support.ts'
import { auth, catalogue, structureCatalogue } from '../../../__tests__/AcademicSetup.support.ts'
import { mapping, populateStructure } from '../../../__tests__/academicStructureFixtures.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import * as api from '../../../../../../services/academics/semesterRegistration.ts'
import SubjectOptionsPage from '../SubjectOptionsPage.tsx'

vi.mock('../../../../../../services/academics/semesterRegistration.ts')

beforeEach(() => {
  populateStructure()
  structureCatalogue.records.curriculum_versions![0].status = 'draft'
  const course = catalogue.records.courses![0]
  catalogue.records.courses!.push({ ...course, course_id: 'optional-course', name: 'DBMS', code: 'DBMS' })
  structureCatalogue.records.curriculum_subjects!.push({
    ...mapping,
    curriculum_subject_id: 'optional-mapping',
    course_id: 'optional-course',
    is_required: false,
  })
  vi.mocked(api.getRegistrationCatalogue).mockResolvedValue({
    institution_id: 'institution-1',
    groups: [],
    students: [],
    assignments: [],
    can_assign: true,
    can_manage_choices: true,
  })
  vi.mocked(api.saveChoiceGroup).mockResolvedValue({ choice_group_id: 'group-1', institution_id: 'institution-1' })
})

it('saves complete alternatives without duplicating required subjects into options', async () => {
  render(
    <SubjectOptionsPage
      context={{
        accessToken: auth.accessToken!,
        identity: 'choice-test',
        institutionId: 'institution-1',
        canReadCatalogues: true,
      }}
    />,
  )
  const form = within(await screen.findByRole('form', { name: 'Subject option group' }))
  await waitFor(() => expect(form.getByRole('combobox', { name: 'Curriculum Version' })).toBeEnabled())
  fireEvent.change(form.getByRole('combobox', { name: 'Curriculum Version' }), { target: { value: 'version-1' } })
  fireEvent.change(form.getByRole('combobox', { name: 'Program Semester' }), { target: { value: 'stage-1' } })
  fireEvent.change(form.getByRole('textbox', { name: 'Group Name' }), { target: { value: 'Semester 3 choices' } })
  const save = form.getByRole('button', { name: 'Save option group' })
  expect(save).toBeEnabled()
  fireEvent.click(save)
  expect(form.getByRole('alert')).toHaveTextContent('Select at least one subject for Option 1.')
  expect(form.getByRole('alert')).toHaveTextContent('Select at least one subject for Option 2.')
  expect(api.saveChoiceGroup).not.toHaveBeenCalled()
  expect(form.getAllByRole('checkbox')).toHaveLength(2)
  for (const checkbox of form.getAllByRole('checkbox', { name: 'DBMS' })) fireEvent.click(checkbox)
  fireEvent.click(save)
  await waitFor(() => expect(api.saveChoiceGroup).toHaveBeenCalledOnce())
  expect(vi.mocked(api.saveChoiceGroup).mock.calls[0][1]).toMatchObject({
    curriculum_version_id: 'version-1',
    program_semester_id: 'stage-1',
    name: 'Semester 3 choices',
    options: [
      { name: 'Option 1', curriculum_subject_ids: ['optional-mapping'] },
      { name: 'Option 2', curriculum_subject_ids: ['optional-mapping'] },
    ],
  })
})

it('does not render an editor when the server denies option management', async () => {
  vi.mocked(api.getRegistrationCatalogue).mockResolvedValue({
    institution_id: 'institution-1',
    groups: [],
    students: [],
    assignments: [],
    can_assign: false,
    can_manage_choices: false,
  })
  render(
    <SubjectOptionsPage
      context={{
        accessToken: 'token-1',
        identity: 'choice-readonly-test',
        institutionId: 'institution-1',
        canReadCatalogues: true,
      }}
    />,
  )
  await screen.findByText('No subject option groups yet.')
  expect(screen.queryByRole('form', { name: 'Subject option group' })).not.toBeInTheDocument()
})

it('recovers from an empty curriculum semester without losing the option group draft', async () => {
  structureCatalogue.records.curriculum_subjects = []
  render(
    <SubjectOptionsPage
      context={{
        accessToken: 'token-1',
        identity: 'choice-empty-recovery',
        institutionId: 'institution-1',
        canReadCatalogues: true,
      }}
    />,
  )
  let form = within(await screen.findByRole('form', { name: 'Subject option group' }))
  await waitFor(() => expect(form.getByRole('combobox', { name: 'Curriculum Version' })).toBeEnabled())
  fireEvent.change(form.getByRole('combobox', { name: 'Curriculum Version' }), { target: { value: 'version-1' } })
  fireEvent.change(form.getByRole('combobox', { name: 'Program Semester' }), { target: { value: 'stage-1' } })
  fireEvent.change(form.getByRole('textbox', { name: 'Group Name' }), { target: { value: 'CSE semester choices' } })
  fireEvent.change(form.getAllByRole('textbox', { name: 'Option Name' })[1], { target: { value: 'Database and labs' } })
  expect(form.getByRole('status')).toHaveTextContent('No subjects are mapped to this curriculum semester yet.')
  fireEvent.click(form.getByRole('button', { name: 'Save option group' }))
  expect(form.getByRole('alert')).toHaveTextContent('Select at least one subject for Database and labs.')
  expect(api.saveChoiceGroup).not.toHaveBeenCalled()
  fireEvent.click(form.getByRole('button', { name: 'Manage semester subjects' }))
  await screen.findByRole('heading', { name: 'Semester Subject Mappings' })
  const add = screen.getByRole('button', { name: 'Add Subject Mapping' })
  await waitFor(() => expect(add).toBeEnabled())
  fireEvent.click(add)
  const dialog = within(await screen.findByRole('dialog', { name: 'Add Subject Mapping' }))
  expect(dialog.getByRole('combobox', { name: 'Curriculum Version' })).toHaveValue('version-1')
  expect(dialog.getByRole('combobox', { name: 'Program Semester' })).toHaveValue('stage-1')
  expect(dialog.getByRole('checkbox', { name: 'Required Subject' })).not.toBeChecked()
  fireEvent.change(dialog.getByRole('combobox', { name: 'Subject', exact: true }), {
    target: { value: 'optional-course' },
  })
  fireEvent.click(dialog.getByRole('button', { name: 'Create Subject Mapping' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: 'Back to option group' }))
  form = within(await screen.findByRole('form', { name: 'Subject option group' }))
  expect(form.getByRole('textbox', { name: 'Group Name' })).toHaveValue('CSE semester choices')
  expect(form.getAllByRole('textbox', { name: 'Option Name' })[1]).toHaveValue('Database and labs')
  const checkboxes = form.getAllByRole('checkbox', { name: 'DBMS' })
  expect(checkboxes).toHaveLength(2)
  for (const checkbox of checkboxes) fireEvent.click(checkbox)
  fireEvent.click(form.getByRole('button', { name: 'Save option group' }))
  await waitFor(() => expect(api.saveChoiceGroup).toHaveBeenCalledOnce())
  expect(vi.mocked(api.saveChoiceGroup).mock.calls[0][1].name).toBe('CSE semester choices')
})

it('explains when every existing mapping is required rather than optional', async () => {
  structureCatalogue.records.curriculum_subjects!.forEach((subject) => {
    subject.is_required = true
  })
  render(
    <SubjectOptionsPage
      context={{
        accessToken: 'token-1',
        identity: 'choice-required-only',
        institutionId: 'institution-1',
        canReadCatalogues: true,
      }}
    />,
  )
  const form = within(await screen.findByRole('form', { name: 'Subject option group' }))
  await waitFor(() => expect(form.getByRole('combobox', { name: 'Curriculum Version' })).toBeEnabled())
  fireEvent.change(form.getByRole('combobox', { name: 'Curriculum Version' }), { target: { value: 'version-1' } })
  fireEvent.change(form.getByRole('combobox', { name: 'Program Semester' }), { target: { value: 'stage-1' } })
  expect(form.getByRole('status')).toHaveTextContent('All mapped subjects are marked Required')
  expect(form.getByText(/Common required subjects:/)).toHaveTextContent('DBMS')
  expect(form.queryByRole('checkbox')).not.toBeInTheDocument()
  fireEvent.click(form.getByRole('button', { name: 'Manage semester subjects' }))
  const edit = await screen.findByRole('button', { name: 'Edit Data Mining', exact: true })
  await waitFor(() => expect(edit).toBeEnabled())
  fireEvent.click(edit)
  const dialog = within(await screen.findByRole('dialog', { name: 'Edit Subject Mapping' }))
  expect(dialog.getByRole('checkbox', { name: 'Required Subject' })).toBeChecked()
  fireEvent.click(dialog.getByRole('checkbox', { name: 'Required Subject' }))
  fireEvent.click(dialog.getByRole('button', { name: 'Save Changes' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: 'Back to option group' }))
  expect(await screen.findAllByRole('checkbox', { name: 'Data Mining' })).toHaveLength(2)
  expect(screen.getByText(/Common required subjects:/)).toHaveTextContent('DBMS')
})

it('lists program semesters in progression order', async () => {
  const first = structureCatalogue.records.program_semesters![0]
  structureCatalogue.records.program_semesters = [
    { ...first, program_semester_id: 'stage-8', semester_number: 8, name: 'Semester 8' },
    { ...first, program_semester_id: 'stage-3', semester_number: 3, name: 'Semester 3' },
    first,
  ]
  render(
    <SubjectOptionsPage
      context={{
        accessToken: 'token-1',
        identity: 'choice-semester-order',
        institutionId: 'institution-1',
        canReadCatalogues: true,
      }}
    />,
  )
  const form = within(await screen.findByRole('form', { name: 'Subject option group' }))
  await waitFor(() => expect(form.getByRole('combobox', { name: 'Curriculum Version' })).toBeEnabled())
  fireEvent.change(form.getByRole('combobox', { name: 'Curriculum Version' }), { target: { value: 'version-1' } })
  const options = within(form.getByRole('combobox', { name: 'Program Semester' })).getAllByRole('option')
  expect(options.map((option) => option.textContent)).toEqual([
    'Select a semester',
    'Semester 1',
    'Semester 3',
    'Semester 8',
  ])
})
