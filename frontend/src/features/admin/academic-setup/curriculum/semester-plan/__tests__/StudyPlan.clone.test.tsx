import { api, renderPlan, selectPlan, structureCatalogue } from './StudyPlan.support.tsx'
import { registrationCatalogue } from '../../../__tests__/AcademicSetup.support.ts'
import * as choiceApi from '../../../../../../services/academics/semesterRegistration.ts'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'

it('clones a published study plan and its subject mappings into a new draft', async () => {
  const source = structureCatalogue.records.curriculum_versions![0]
  source.status = 'published'
  source.published_at = '2026-10-01T00:00:00Z'
  structureCatalogue.records.curriculum_subjects![0].is_required = false
  registrationCatalogue.groups = [
    {
      choice_group_id: 'group-1',
      institution_id: 'institution-1',
      curriculum_version_id: source.curriculum_version_id,
      program_semester_id: 'stage-1',
      name: 'Elective choices',
      options: [
        { choice_option_id: 'option-1', name: 'Option 1', curriculum_subject_ids: ['mapping-1'] },
        { choice_option_id: 'option-2', name: 'Option 2', curriculum_subject_ids: ['mapping-1'] },
      ],
    },
  ]
  renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Clone as draft' }))
  fireEvent.click(screen.getByRole('button', { name: 'Create draft copy' }))
  await waitFor(() => expect(api.createStructureRecord).toHaveBeenCalledTimes(2))
  expect(api.createStructureRecord).toHaveBeenNthCalledWith(
    1,
    'token-1',
    'curriculum_versions',
    expect.objectContaining({
      program_id: source.program_id,
      academic_year_id: source.academic_year_id,
      name: 'CSE Curriculum Copy',
      version: '1.0-copy',
      total_semesters: source.total_semesters,
      is_active: true,
    }),
  )
  expect(choiceApi.saveChoiceGroup).toHaveBeenCalledWith(
    'token-1',
    expect.objectContaining({
      curriculum_version_id: 'new-curriculum_versions',
      program_semester_id: 'stage-1',
      name: 'Elective choices',
      options: [
        { name: 'Option 1', curriculum_subject_ids: ['new-curriculum_subjects'] },
        { name: 'Option 2', curriculum_subject_ids: ['new-curriculum_subjects'] },
      ],
    }),
  )
  expect(api.createStructureRecord).toHaveBeenNthCalledWith(
    2,
    'token-1',
    'curriculum_subjects',
    expect.objectContaining({
      curriculum_version_id: 'new-curriculum_versions',
      course_id: structureCatalogue.records.curriculum_subjects![0].course_id,
      is_required: false,
      is_active: true,
    }),
  )
  expect(await screen.findByRole('heading', { name: 'CSE Curriculum Copy', level: 2 })).toBeInTheDocument()
})

it('keeps a partial clone from being retried when the saved curriculum belongs to another tenant', async () => {
  const source = structureCatalogue.records.curriculum_versions![0]
  source.status = 'published'
  source.published_at = '2026-10-01T00:00:00Z'
  vi.mocked(api.createStructureRecord).mockResolvedValueOnce({
    ...source,
    curriculum_version_id: 'partial-copy',
    institution_id: 'other-tenant',
    status: 'draft',
    is_active: true,
  })
  renderPlan()
  await selectPlan()
  fireEvent.click(screen.getByRole('button', { name: 'Clone as draft' }))
  fireEvent.click(screen.getByRole('button', { name: 'Create draft copy' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be verified for this institution')
  expect(screen.getByRole('button', { name: 'Create draft copy' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
  expect(screen.queryByRole('button', { name: 'Clone as draft' })).not.toBeInTheDocument()
  expect(api.createStructureRecord).toHaveBeenCalledOnce()
})
