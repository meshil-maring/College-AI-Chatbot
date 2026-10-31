import { api, catalogue, renderPlan, selectPlan, structureCatalogue } from './StudyPlan.support.tsx'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { expect, it, vi } from 'vitest'

it('groups subjects by numeric semester and keeps other programs and curricula separate', async () => {
  structureCatalogue.records.program_semesters!.reverse()
  structureCatalogue.records.curriculum_subjects!.push({
    ...structureCatalogue.records.curriculum_subjects![0],
    curriculum_subject_id: 'other-mapping',
    curriculum_version_id: 'other-version',
    program_semester_id: 'stage-2',
    course_id: 'english',
  })
  renderPlan()
  expect(screen.queryByRole('region', { name: 'Semester 1 subjects' })).not.toBeInTheDocument()
  await selectPlan()
  const semesters = screen.getAllByRole('region', { name: /Semester \d subjects/ })
  expect(semesters.map((item) => item.getAttribute('aria-label'))).toEqual([
    'Semester 1 subjects',
    'Semester 2 subjects',
  ])
  expect(semesters[0]).toHaveTextContent('Data Mining')
  expect(semesters[1]).toHaveTextContent('No subjects yet')
  expect(semesters[1]).not.toHaveTextContent('English')
})

it('adds a subject to the chosen semester without asking for the curriculum and semester again', async () => {
  renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Add subject to Semester 2' }))
  const drawer = within(screen.getByRole('dialog', { name: 'Add subject in Semester 2' }))
  expect(drawer.queryByRole('combobox', { name: /Curriculum|Program Semester/ })).not.toBeInTheDocument()
  fireEvent.change(drawer.getByRole('combobox', { name: 'Subject', exact: true }), { target: { value: 'english' } })
  fireEvent.click(drawer.getByRole('button', { name: 'Add subject', exact: true }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  expect(api.createStructureRecord).toHaveBeenCalledExactlyOnceWith('token-1', 'curriculum_subjects', {
    curriculum_version_id: 'version-1',
    program_semester_id: 'stage-2',
    course_id: 'english',
    course_type: 'core',
    is_required: true,
    is_active: true,
  })
  expect(screen.getByRole('region', { name: 'Semester 2 subjects' })).toHaveTextContent('English')
  expect(screen.getByRole('region', { name: 'Semester 1 subjects' })).not.toHaveTextContent('English')
})

it('excludes already listed subjects, including inactive mappings, from the add choices', async () => {
  structureCatalogue.records.curriculum_subjects![0].is_active = false
  renderPlan()
  await selectPlan()
  expect(screen.getByRole('region', { name: 'Semester 1 subjects' })).toHaveTextContent('Not included')
  fireEvent.click(screen.getByRole('button', { name: 'Add subject to Semester 1' }))
  const drawer = within(screen.getByRole('dialog'))
  expect(drawer.queryByRole('option', { name: /Data Mining/ })).not.toBeInTheDocument()
  expect(drawer.getByRole('option', { name: /English/ })).toBeInTheDocument()
})

it('edits requirements and confirms excluding a subject while retaining its mapping', async () => {
  renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Edit Data Mining in Semester 1' }))
  const drawer = within(screen.getByRole('dialog'))
  fireEvent.click(drawer.getByRole('checkbox', { name: 'Every student must take this subject' }))
  fireEvent.click(drawer.getByRole('checkbox', { name: 'Include in study plan' }))
  fireEvent.click(drawer.getByRole('button', { name: 'Save subject' }))
  expect(api.updateStructureRecord).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Confirm change' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  expect(api.updateStructureRecord).toHaveBeenCalledExactlyOnceWith('token-1', 'curriculum_subjects', 'mapping-1', {
    is_required: false,
    is_active: false,
  })
  expect(screen.getByRole('region', { name: 'Semester 1 subjects' })).toHaveTextContent('Student choice · Not included')
})

it.each(['published', 'archived'] as const)('keeps %s study plans read-only', async (status) => {
  structureCatalogue.records.curriculum_versions![0].status = status
  renderPlan()
  await selectPlan()
  expect(
    screen.queryByRole('button', { name: /Add subject|Edit Data Mining|Review and publish/ }),
  ).not.toBeInTheDocument()
  expect(screen.getByText(/Its subjects are kept unchanged/)).toBeInTheDocument()
  expect(api.createStructureRecord).not.toHaveBeenCalled()
})

it('respects server read-only grants', async () => {
  structureCatalogue.manageable = []
  renderPlan()
  await selectPlan()
  expect(screen.getByRole('button', { name: 'Add subject to Semester 2' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Review and publish' })).toBeDisabled()
})

it('sets up a missing semester inside the plan only when requested', async () => {
  structureCatalogue.records.program_semesters!.pop()
  renderPlan()
  await selectPlan()
  const semester = within(screen.getByRole('region', { name: 'Semester 2 subjects' }))
  expect(semester.getByRole('button', { name: 'Add subject to Semester 2' })).toBeDisabled()
  expect(api.createStructureRecord).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Set up 1 missing semester' }))
  await waitFor(() => expect(semester.getByRole('button', { name: 'Add subject to Semester 2' })).toBeEnabled())
  expect(screen.getByRole('heading', { name: 'Subjects by semester', level: 1 })).toBeInTheDocument()
  expect(api.createStructureRecord).toHaveBeenCalledExactlyOnceWith('token-1', 'program_semesters', {
    program_id: 'program-1',
    semester_number: 2,
    name: 'Semester 2',
    code: 'SEM-2',
    is_active: true,
  })
})

it('keeps a failed subject draft and prevents duplicate submissions', async () => {
  let reject!: (cause: Error) => void
  vi.mocked(api.createStructureRecord).mockImplementation(
    () =>
      new Promise((_resolve, fail) => {
        reject = fail
      }),
  )
  renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Add subject to Semester 2' }))
  fireEvent.change(screen.getByRole('combobox', { name: 'Subject', exact: true }), { target: { value: 'english' } })
  fireEvent.click(screen.getByRole('button', { name: 'Add subject', exact: true }))
  expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled()
  fireEvent.submit(screen.getByRole('form', { name: 'Semester subject' }))
  expect(api.createStructureRecord).toHaveBeenCalledOnce()
  reject(new Error('Subject could not be saved'))
  expect(await screen.findByRole('alert')).toHaveTextContent('Subject could not be saved')
  expect(screen.getByRole('combobox', { name: 'Subject', exact: true })).toHaveValue('english')
})

it('hides foreign-tenant subjects from the plan and selection controls', async () => {
  catalogue.records.courses!.push({
    ...catalogue.records.courses![0],
    institution_id: 'other',
    course_id: 'foreign',
    name: 'Private foreign subject',
  })
  structureCatalogue.records.curriculum_subjects!.push({
    ...structureCatalogue.records.curriculum_subjects![0],
    institution_id: 'other',
    curriculum_subject_id: 'foreign-mapping',
    course_id: 'foreign',
  })
  renderPlan()
  await selectPlan()
  expect(screen.queryByText(/Private foreign subject/)).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Add subject to Semester 2' }))
  expect(screen.queryByRole('option', { name: /Private foreign subject/ })).not.toBeInTheDocument()
})
