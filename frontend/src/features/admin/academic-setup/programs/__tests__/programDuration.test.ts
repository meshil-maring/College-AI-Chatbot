import { describe, expect, it } from 'vitest'
import { durationWarning } from '../programModel.ts'

describe('program duration warning', () => {
  it('stays quiet for normal durations, including fractional ones', () => {
    for (const value of ['', '1', '2.5', '4', '6']) expect(durationWarning(value)).toBeUndefined()
  })

  it('flags a duration that looks like a semester count and suggests the year value', () => {
    expect(durationWarning('8')).toBe(
      '8 years is unusually long. Duration is in years, not semesters. If this is 8 semesters, enter 4.',
    )
  })

  it('still warns without a suggestion when the value cannot be halved into years', () => {
    expect(durationWarning('7')).toBe('7 years is unusually long. Duration is in years, not semesters.')
  })

  it('ignores invalid input, which the required-field check already reports', () => {
    expect(durationWarning('abc')).toBeUndefined()
  })
})
