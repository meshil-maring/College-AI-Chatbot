import { api, renderCalendar } from '../../calendar/__tests__/Calendar.support.tsx'
import { structureCatalogue } from '../../__tests__/AcademicSetup.support.ts'
import { cohort, section, stage, version } from '../../__tests__/academicStructureFixtures.ts'
import * as structureApi from '../../../../../services/admin/academicStructure.ts'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

beforeEach(() => {
  structureCatalogue.records.program_semesters = [structuredClone(stage)]
  structureCatalogue.records.curriculum_versions = [structuredClone(version)]
  structureCatalogue.records.admission_cohorts = [structuredClone(cohort)]
  structureCatalogue.records.academic_sections = [structuredClone(section)]
})

async function openRollover() {
  renderCalendar()
  const button = await screen.findByRole('button', { name: 'Roll over to next year' })
  await waitFor(() => expect(button).toBeEnabled())
  fireEvent.click(button)
  return screen.findByRole('dialog', { name: 'Roll over to next year' })
}

describe('Roll over to next year', () => {
  it('previews next year before creating anything', async () => {
    const dialog = await openRollover()
    const preview = await within(dialog).findByRole('region', { name: 'Roll-over preview' })
    expect(within(preview).getByText('2027–2028')).toBeInTheDocument()
    expect(within(preview).getByText('CSE 2026 · Section A')).toBeInTheDocument()
    expect(within(preview).getByText(/Semester 3 · Semester 1 · 0 subjects/)).toBeInTheDocument()
    expect(api.createAcademicRecord).not.toHaveBeenCalled()
    expect(structureApi.createStructureRecord).not.toHaveBeenCalled()
  })

  it('creates the year, its terms and the continuing section, then has nothing left to do', async () => {
    const dialog = await openRollover()
    const run = await within(dialog).findByRole('button', { name: 'Roll over' })
    fireEvent.click(run)
    expect(await within(dialog).findByText(/Next year is ready/)).toBeInTheDocument()
    expect(api.createAcademicRecord).toHaveBeenCalledWith('token-1', 'academic_years', {
      name: '2027–2028',
      code: '2027-28',
      start_date: '2027-07-01',
      end_date: '2028-06-30',
      is_current: false,
      is_active: true,
    })
    expect(vi.mocked(api.createAcademicRecord).mock.calls.filter(([, entity]) => entity === 'semesters')).toHaveLength(
      2,
    )
    expect(structureApi.createStructureRecord).toHaveBeenCalledWith(
      'token-1',
      'program_semesters',
      expect.objectContaining({ semester_number: 3 }),
    )
    expect(structureApi.createStructureRecord).toHaveBeenCalledWith(
      'token-1',
      'academic_sections',
      expect.objectContaining({ code: 'CSE26A', admission_cohort_id: cohort.admission_cohort_id, capacity: 60 }),
    )
    expect(within(dialog).getByRole('button', { name: 'Nothing to create' })).toBeDisabled()
    expect(within(dialog).getByRole('button', { name: 'Done' })).toBeEnabled()
  })
})
