import { describe, expect, it, vi } from 'vitest'
import { nextYearDate, nextYearLabel, planHasWork, planRollover } from '../rolloverPlan.ts'
import { rolloverStepCount, runRollover, type RolloverApi } from '../runRollover.ts'
import { scenario } from './rolloverScenario.ts'

describe('roll-over helpers', () => {
  it('moves dates and year labels forward by one year', () => {
    expect(nextYearDate('2026-08-01')).toBe('2027-08-01')
    expect(nextYearDate('2028-02-29')).toBe('2029-02-28')
    expect(nextYearLabel('2026 - 2027')).toBe('2027 - 2028')
    expect(nextYearLabel('2026–27')).toBe('2027–28')
    expect(nextYearLabel('ODD26')).toBe('ODD27')
    expect(nextYearLabel('AY2026')).toBe('AY2027')
    expect(nextYearLabel('Odd Term S1')).toBe('Odd Term S1')
  })
})

describe('roll-over plan', () => {
  it('creates next year and its terms, and continues each section two semesters on', () => {
    const { catalogue, structure } = scenario()
    const plan = planRollover('y26', catalogue, structure)!
    expect(plan.year).toMatchObject({
      existing: undefined,
      create: { name: '2027 - 2028', code: 'AY2027', start_date: '2027-08-01', end_date: '2028-07-31' },
    })
    expect(plan.terms.map((term) => [term.create.name, term.create.code, term.create.start_date])).toEqual([
      ['Odd Term 2027', 'ODD27', '2027-08-01'],
      ['Even Term 2028', 'EVEN28', '2028-01-30'],
    ])
    expect(
      plan.sections.map((s) => [s.section.name, s.stageNumber, s.termNumber, s.stageId, s.subjects.length]),
    ).toEqual([
      ['Section A (Semester 3)', 3, 1, 'p1-s3', 2],
      ['Section B', 3, 1, 'p1-s3', 2],
      ['Section A (Semester 4)', 4, 2, undefined, 0],
    ])
    expect(plan.skipped).toEqual([{ label: 'CSE 2023 · Section A', reason: 'The batch ends in 2027.' }])
  })

  it('reuses what already exists, so a second run has nothing left to do', () => {
    const { catalogue, structure } = scenario()
    catalogue.records.academic_years!.push({
      ...catalogue.records.academic_years![0],
      academic_year_id: 'y27',
      start_date: '2027-08-01',
    })
    const plan = planRollover('y26', catalogue, structure)!
    expect(plan.year.existing?.academic_year_id).toBe('y27')
    expect(plan.terms.every((term) => !term.existing)).toBe(true)
    structure.records.academic_sections!.push({
      ...structure.records.academic_sections![0],
      academic_section_id: 'a3',
      program_semester_id: 'p1-s3',
      semester_id: 'odd27',
    })
    structure.records.academic_offerings = ['m3a', 'm3b'].map(
      (id) => ({ academic_offering_id: id, academic_section_id: 'a3', curriculum_subject_id: id }) as never,
    )
    const again = planRollover('y26', catalogue, structure)!
    expect(again.sections.map((s) => s.section.code)).toEqual(['B', 'A'])
    expect(planHasWork(again)).toBe(true)
  })

  it('stops continuing a batch at the end of its curriculum', () => {
    const { catalogue, structure } = scenario()
    structure.records.admission_cohorts![1].end_year = 2031
    const plan = planRollover('y26', catalogue, structure)!
    expect(plan.skipped).toEqual([{ label: 'CSE 2023 · Section A', reason: 'The curriculum ends at Semester 8.' }])
  })
})

describe('roll-over run', () => {
  function api(failOn?: string): RolloverApi {
    let n = 0
    const make = (prefix: string) =>
      vi.fn(async (payload: object) => {
        if (failOn && JSON.stringify(payload).includes(failOn)) throw new Error('Server rejected')
        n += 1
        return {
          ...payload,
          academic_year_id: `y${n}`,
          semester_id: `t${n}`,
          program_semester_id: `${prefix}${n}`,
          academic_section_id: `s${n}`,
        }
      })
    return {
      createYear: make('y') as never,
      createTerm: make('t') as never,
      createStage: make('st') as never,
      createSection: make('s') as never,
      createOffering: make('o') as never,
    }
  }

  it('creates everything in dependency order and reports progress', async () => {
    const { catalogue, structure } = scenario()
    const plan = planRollover('y26', catalogue, structure)!
    const calls = api()
    const progress = vi.fn()
    expect(rolloverStepCount(plan)).toBe(1 + 2 + 1 + 3 + 4)
    await expect(runRollover(plan, calls, progress)).resolves.toEqual({ done: 11, total: 11 })
    expect(calls.createTerm).toHaveBeenCalledWith(
      expect.objectContaining({ academic_year_id: 'y1', is_current: false }),
    )
    expect(calls.createStage).toHaveBeenCalledWith(expect.objectContaining({ semester_number: 4, code: 'SEM-4' }))
    expect(calls.createSection).toHaveBeenCalledWith(
      expect.objectContaining({ code: 'A', admission_cohort_id: 'b26', program_semester_id: 'p1-s3', capacity: 60 }),
    )
    expect(calls.createOffering).toHaveBeenCalledTimes(4)
    expect(progress).toHaveBeenLastCalledWith({ done: 11, total: 11, current: expect.any(String) })
  })

  it('stops at the first failure and names the step', async () => {
    const { catalogue, structure } = scenario()
    const plan = planRollover('y26', catalogue, structure)!
    await expect(runRollover(plan, api('Section B'), vi.fn())).rejects.toThrow('CSE 2026 · Section B: Server rejected')
  })
})
