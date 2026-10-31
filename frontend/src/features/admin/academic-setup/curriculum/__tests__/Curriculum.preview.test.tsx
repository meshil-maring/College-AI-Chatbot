import '../../__tests__/AcademicSetup.support.ts'
import { catalogue, structureCatalogue } from '../../__tests__/AcademicSetup.support.ts'
import { populateStructure } from '../../__tests__/academicStructureFixtures.ts'
import * as api from '../../../../../services/admin/academicStructure.ts'
import AcademicWorkspace from '../../overview/AcademicWorkspace.tsx'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useState } from 'react'
import type { AcademicPage } from '../../overview/academicOverviewModel.ts'

beforeEach(populateStructure)
function renderVersions() {
  function Workspace() {
    const [page, setPage] = useState<AcademicPage>('curriculum')
    return <AcademicWorkspace page={page} search="" onNavigate={setPage} onClearSearch={vi.fn()} />
  }
  return render(<Workspace />)
}
describe('Persisted curriculum versions', () => {
  it('creates a real draft instead of a disconnected preview', async () => {
    renderVersions()
    const trigger = screen.getByRole('button', { name: 'Add Curriculum' })
    await waitFor(() => expect(trigger).toBeEnabled())
    fireEvent.click(trigger)
    const drawer = within(screen.getByRole('dialog', { name: 'Add Curriculum' }))
    fireEvent.change(drawer.getByRole('combobox', { name: 'Program' }), { target: { value: 'program-1' } })
    fireEvent.change(drawer.getByRole('combobox', { name: 'Academic Year' }), { target: { value: 'year-1' } })
    fireEvent.change(drawer.getByRole('textbox', { name: 'Curriculum Name' }), { target: { value: 'CSE 2027' } })
    fireEvent.change(drawer.getByRole('textbox', { name: 'Version' }), { target: { value: '2.0' } })
    fireEvent.click(drawer.getByRole('button', { name: 'Create Curriculum' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(api.createStructureRecord).toHaveBeenCalledWith(
      'token-1',
      'curriculum_versions',
      expect.objectContaining({
        program_id: 'program-1',
        academic_year_id: 'year-1',
        name: 'CSE 2027',
        version: '2.0',
        total_semesters: 8,
      }),
    )
    expect(vi.mocked(api.createStructureRecord).mock.calls[0][2]).not.toHaveProperty('status')
  })
  it('requires confirmation before publishing and freezes published metadata', async () => {
    structureCatalogue.records.curriculum_versions![0].status = 'draft'
    structureCatalogue.records.curriculum_versions![0].published_at = null
    renderVersions()
    fireEvent.click(await screen.findByRole('button', { name: 'Edit CSE Curriculum' }))
    const drawer = within(screen.getByRole('dialog', { name: 'Edit Curriculum' }))
    fireEvent.change(drawer.getByRole('combobox', { name: 'Publication Status' }), { target: { value: 'published' } })
    fireEvent.click(drawer.getByRole('button', { name: 'Save Changes' }))
    expect(screen.getByRole('alertdialog', { name: 'Confirm status change' })).toBeInTheDocument()
    expect(api.updateStructureRecord).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Change' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Edit CSE Curriculum' }))
    expect(screen.getByRole('textbox', { name: 'Curriculum Name' })).toBeDisabled()
    expect(api.updateStructureRecord).toHaveBeenCalledWith('token-1', 'curriculum_versions', 'version-1', {
      status: 'published',
    })
  })
  it('maps reusable subjects to program progression within a draft curriculum', async () => {
    structureCatalogue.records.curriculum_versions![0].status = 'draft'
    structureCatalogue.records.curriculum_subjects = []
    renderVersions()
    await screen.findAllByRole('button', { name: 'View CSE Curriculum' })
    fireEvent.click(screen.getByRole('tab', { name: 'Subjects by semester' }))
    fireEvent.change(screen.getByRole('combobox', { name: 'Choose a curriculum' }), { target: { value: 'version-1' } })
    const trigger = screen.getByRole('button', { name: 'Add subject to Semester 1' })
    await waitFor(() => expect(trigger).toBeEnabled())
    fireEvent.click(trigger)
    const drawer = within(screen.getByRole('dialog', { name: 'Add subject in Semester 1' }))
    fireEvent.change(drawer.getByRole('combobox', { name: 'Subject', exact: true }), {
      target: { value: catalogue.records.courses![0].course_id },
    })
    fireEvent.click(drawer.getByRole('button', { name: 'Add subject', exact: true }))
    await waitFor(() =>
      expect(api.createStructureRecord).toHaveBeenCalledWith(
        'token-1',
        'curriculum_subjects',
        expect.objectContaining({
          curriculum_version_id: 'version-1',
          program_semester_id: 'stage-1',
          course_type: 'core',
          is_required: true,
        }),
      ),
    )
  })
  it('displays stored publication history and retains the existing mapping workflow', async () => {
    renderVersions()
    await screen.findByRole('button', { name: 'View CSE Curriculum' })
    fireEvent.click(screen.getByRole('tab', { name: 'Version History' }))
    expect(screen.getByRole('region', { name: 'Published curriculum history' })).toHaveTextContent(
      'CSE Curriculum · v1.0 · Published',
    )
    fireEvent.click(screen.getByRole('tab', { name: 'Legacy program mappings' }))
    expect(await screen.findByRole('heading', { name: 'Legacy program mappings' })).toBeInTheDocument()
    expect(
      screen.getByText(/They do not populate versioned curricula or determine the subjects assigned to new batches/),
    ).toBeInTheDocument()
    expect(await screen.findByRole('region', { name: 'Curriculum summary' })).toBeInTheDocument()
  })

  it('compares published subject mappings between versions of the same program', async () => {
    const first = structureCatalogue.records.curriculum_versions![0]
    structureCatalogue.records.curriculum_versions!.push({
      ...first,
      curriculum_version_id: 'version-2',
      name: 'CSE Curriculum',
      version: '2.0',
    })
    structureCatalogue.records.curriculum_subjects!.push({
      ...structureCatalogue.records.curriculum_subjects![0],
      curriculum_subject_id: 'mapping-2',
      curriculum_version_id: 'version-2',
      course_type: 'elective',
      credits: 4,
    })
    renderVersions()
    await screen.findAllByRole('button', { name: 'View CSE Curriculum' })
    fireEvent.click(screen.getByRole('tab', { name: 'Version History' }))
    fireEvent.change(screen.getByRole('combobox', { name: 'Earlier version' }), {
      target: { value: first.curriculum_version_id },
    })
    fireEvent.change(screen.getByRole('combobox', { name: 'Later version' }), { target: { value: 'version-2' } })
    expect(screen.getByRole('region', { name: 'Compare curriculum versions' })).toHaveTextContent(
      'Changed subject type',
    )
    expect(screen.getByRole('region', { name: 'Compare curriculum versions' })).toHaveTextContent('credits')
    expect(screen.getByRole('region', { name: 'Compare curriculum versions' })).toHaveTextContent('Data Mining')
  })
})
