import { api, renderPlan, selectPlan, structureCatalogue } from '../../semester-plan/__tests__/StudyPlan.support.tsx'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'

it('creates only missing numbers and preserves custom, inactive and out-of-range stages and every existing link', async () => {
  const stages = structureCatalogue.records.program_semesters!
  Object.assign(stages[0], { name: 'First year foundation', code: 'FOUND', is_active: false })
  stages.pop()
  stages.push({
    ...stages[0],
    program_semester_id: 'stage-8',
    semester_number: 8,
    name: 'Final project',
    code: 'PROJECT',
    is_active: true,
  })
  const before = structuredClone(structureCatalogue.records)
  renderPlan()
  await selectPlan()
  expect(api.createStructureRecord).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Set up 1 missing semester' }))
  await screen.findByText('Semesters are ready. Existing semester records have been reused.')
  expect(stages.slice(0, 2)).toEqual(before.program_semesters)
  for (const entity of [
    'curriculum_versions',
    'curriculum_subjects',
    'admission_cohorts',
    'academic_sections',
    'academic_offerings',
  ] as const)
    expect(structureCatalogue.records[entity]).toEqual(before[entity])
  expect(api.createStructureRecord).toHaveBeenCalledOnce()
  expect(api.updateStructureRecord).not.toHaveBeenCalled()
  expect(screen.getByRole('button', { name: 'Add subject to Semester 1' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Add subject to Semester 2' })).toBeEnabled()
})

it('rechecks the server before setup and reuses semesters created by another administrator', async () => {
  const second = structureCatalogue.records.program_semesters!.pop()!
  renderPlan()
  await selectPlan()
  structureCatalogue.records.program_semesters!.push(second)
  fireEvent.click(screen.getByRole('button', { name: 'Set up 1 missing semester' }))
  await screen.findByText(
    'All semesters are set up. Use Semester settings on a card to change its name, code or active status.',
  )
  expect(api.createStructureRecord).not.toHaveBeenCalled()
})

it('creates every missing semester in numeric order and avoids existing custom code collisions', async () => {
  structureCatalogue.records.program_semesters = []
  renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Set up 2 missing semesters' }))
  await screen.findByText('Semesters are ready. Existing semester records have been reused.')
  expect(vi.mocked(api.createStructureRecord).mock.calls.map((call) => call[2])).toEqual([
    { program_id: 'program-1', semester_number: 1, name: 'Semester 1', code: 'SEM-1', is_active: true },
    { program_id: 'program-1', semester_number: 2, name: 'Semester 2', code: 'SEM-2', is_active: true },
  ])
  expect(new Set(structureCatalogue.records.program_semesters!.map((item) => item.program_semester_id)).size).toBe(2)
})

it('keeps a custom code and gives a missing semester its own unused code', async () => {
  structureCatalogue.records.program_semesters![0].code = ' sem-2 '
  structureCatalogue.records.program_semesters!.pop()
  renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Set up 1 missing semester' }))
  await waitFor(() => expect(api.createStructureRecord).toHaveBeenCalledOnce())
  expect(api.createStructureRecord).toHaveBeenCalledWith(
    'token-1',
    'program_semesters',
    expect.objectContaining({ code: 'SEM-2-2', semester_number: 2 }),
  )
})

it('retains successful stages after a failure and retries only numbers still missing', async () => {
  structureCatalogue.records.program_semesters = []
  const save = vi.mocked(api.createStructureRecord).getMockImplementation()!
  vi.mocked(api.createStructureRecord)
    .mockImplementationOnce(save)
    .mockRejectedValueOnce(new Error('Connection interrupted'))
  renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Set up 2 missing semesters' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Connection interrupted')
  const first = structuredClone(structureCatalogue.records.program_semesters![0])
  const retry = await screen.findByRole('button', { name: 'Set up 1 missing semester' })
  await waitFor(() => expect(retry).toBeEnabled())
  fireEvent.click(retry)
  await screen.findByText('Semesters are ready. Existing semester records have been reused.')
  expect(structureCatalogue.records.program_semesters![0]).toEqual(first)
  expect(api.createStructureRecord).toHaveBeenCalledTimes(3)
  expect(
    vi
      .mocked(api.createStructureRecord)
      .mock.calls.map((call) => (call[2] as { semester_number: number }).semester_number),
  ).toEqual([1, 2, 2])
})

it.each(['published', 'archived'] as const)('keeps %s curriculum semester setup read-only', async (status) => {
  structureCatalogue.records.curriculum_versions![0].status = status
  structureCatalogue.records.program_semesters = []
  renderPlan()
  await selectPlan()
  expect(screen.queryByRole('region', { name: 'Semester setup' })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Semester settings|Set up \d/ })).not.toBeInTheDocument()
  expect(api.createStructureRecord).not.toHaveBeenCalled()
})

it('keeps program-stage permissions separate from subject-management permissions', async () => {
  structureCatalogue.manageable = ['curriculum_subjects', 'curriculum_versions']
  structureCatalogue.records.program_semesters!.pop()
  renderPlan()
  await selectPlan()
  expect(screen.getByRole('button', { name: 'Set up 1 missing semester' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Semester settings for Semester 1' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Add subject to Semester 1' })).toBeEnabled()
  expect(api.createStructureRecord).not.toHaveBeenCalled()
})
