import { describe, expect, it } from 'vitest'
import { deriveBatch, emptyBatch, validateBatch, type BatchProgram } from '../batchModel.ts'

const programs: BatchProgram[] = [
  { id: 'btech', name: 'B.Tech', code: 'BT', duration: 4, color: 'gold' },
  { id: 'bsc', name: 'B.Sc', code: 'BS', duration: 2.5, color: 'gold' },
]
const curricula = [
  { id: 'btech-v1', programId: 'btech', version: '1.0', active: true },
  { id: 'bsc-v1', programId: 'bsc', version: '1.0', active: true },
  { id: 'bsc-v2', programId: 'bsc', version: '2.0', active: true },
]
const years = [{ academic_year_id: 'ay-2025', start_date: '2025-07-01' }]

describe('batch defaults', () => {
  it('starts without invented years', () => {
    expect(emptyBatch()).toMatchObject({ startYear: '', endYear: '' })
  })

  it('fills the start year from the intake year and the end year from the program duration', () => {
    let draft = deriveBatch({ ...emptyBatch(), programId: 'btech' }, 'programId', programs, curricula, years)
    expect(draft.curriculumId).toBe('btech-v1')
    draft = deriveBatch({ ...draft, academicYear: 'ay-2025' }, 'academicYear', programs, curricula, years)
    expect(draft).toMatchObject({ startYear: '2025', endYear: '2029' })
  })

  it('leaves the curriculum for the administrator when several are published', () => {
    const draft = deriveBatch(
      { ...emptyBatch(), academicYear: 'ay-2025', startYear: '2025', programId: 'bsc' },
      'programId',
      programs,
      curricula,
      years,
    )
    expect(draft).toMatchObject({ curriculumId: '', endYear: '2028' })
  })
})

describe('batch validation', () => {
  const valid = {
    ...emptyBatch(),
    name: 'CSE 2025',
    code: 'CSE25',
    programId: 'btech',
    curriculumId: 'btech-v1',
    academicYear: 'ay-2025',
    startYear: '2025',
    endYear: '2029',
  }

  it('accepts the derived years and a shorter lateral-entry span', () => {
    expect(validateBatch(valid, [], programs, curricula, undefined, years)).toBeUndefined()
    expect(validateBatch({ ...valid, endYear: '2028' }, [], programs, curricula, undefined, years)).toBeUndefined()
  })

  it('blocks a start year that differs from the intake academic year', () => {
    expect(
      validateBatch({ ...valid, startYear: '2026', endYear: '2030' }, [], programs, curricula, undefined, years),
    ).toBe('Start year must be 2025, when the intake academic year starts.')
  })

  it('blocks a batch longer than its program', () => {
    expect(validateBatch({ ...valid, endYear: '2030' }, [], programs, curricula, undefined, years)).toBe(
      "End year cannot be later than 2029 for this program's duration.",
    )
  })
})
