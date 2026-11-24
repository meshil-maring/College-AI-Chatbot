import { describe, expect, it } from 'vitest'
import { batchYears, nameCodeError, sectionLetters, semesterCount, splitYearIntoTerms } from '../quickSetupModel.ts'

describe('quick setup helpers', () => {
  it('splits a year into equal back-to-back terms that cover it exactly', () => {
    const terms = splitYearIntoTerms('2026-08-01', '2027-07-31', 2)
    expect(terms).toEqual([
      { name: 'Term 1', code: 'T1', semester_number: 1, start_date: '2026-08-01', end_date: '2027-01-29' },
      { name: 'Term 2', code: 'T2', semester_number: 2, start_date: '2027-01-30', end_date: '2027-07-31' },
    ])
    const three = splitYearIntoTerms('2026-08-01', '2027-07-31', 3)
    expect(three[0].start_date).toBe('2026-08-01')
    expect(three[2].end_date).toBe('2027-07-31')
    expect(three[1].start_date).toBe('2026-11-30')
  })

  it('returns no terms for invalid dates or counts', () => {
    expect(splitYearIntoTerms('2027-07-31', '2026-08-01', 2)).toEqual([])
    expect(splitYearIntoTerms('', '2027-07-31', 2)).toEqual([])
    expect(splitYearIntoTerms('2026-08-01', '2027-07-31', 0)).toEqual([])
  })

  it('derives semesters, batch years and section letters', () => {
    expect(semesterCount(4)).toBe(8)
    expect(semesterCount(2.5)).toBe(5)
    expect(batchYears('2026-08-01', 4)).toEqual({ start_year: 2026, end_year: 2030 })
    expect(batchYears('2026-08-01', 2.5)).toEqual({ start_year: 2026, end_year: 2029 })
    expect(sectionLetters(3)).toEqual(['A', 'B', 'C'])
    expect(sectionLetters(0)).toEqual(['A'])
  })

  it('explains the first problem with a name and code', () => {
    expect(nameCodeError(' ', 'X')).toBe('Enter a name.')
    expect(nameCodeError('Name', '')).toBe('Enter a code.')
    expect(nameCodeError('Name', 'X'.repeat(33))).toBe('Use a code of 32 characters or fewer.')
    expect(nameCodeError('Name', 'CODE')).toBe('')
  })
})
