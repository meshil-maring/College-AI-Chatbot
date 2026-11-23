import { describe, expect, it } from 'vitest'
import { largestOfferingCapacity, termFitsBatch } from '../sectionModel.ts'

const batch = { id: 'b', name: 'CSE 2025', programId: 'p', academicYear: '2025-26', startYear: 2025, endYear: 2029 }

describe('section consistency rules', () => {
  it('accepts only teaching terms within the batch years', () => {
    expect(termFitsBatch({ start_date: '2025-07-01', end_date: '2025-12-15' }, batch)).toBe(true)
    expect(termFitsBatch({ start_date: '2029-01-05', end_date: '2029-05-30' }, batch)).toBe(true)
    expect(termFitsBatch({ start_date: '2024-07-01', end_date: '2024-12-15' }, batch)).toBe(false)
    expect(termFitsBatch({ start_date: '2029-07-01', end_date: '2030-01-10' }, batch)).toBe(false)
  })

  it('does not block when the batch years are unknown', () => {
    expect(termFitsBatch({ start_date: '1999-01-01', end_date: '1999-06-01' }, undefined)).toBe(true)
  })

  it('finds the largest active offering capacity in a section', () => {
    const offerings = [
      { academic_section_id: 's1', capacity: 40, is_active: true },
      { academic_section_id: 's1', capacity: 70, is_active: false },
      { academic_section_id: 's1', capacity: null, is_active: true },
      { academic_section_id: 's2', capacity: 90, is_active: true },
    ]
    expect(largestOfferingCapacity('s1', offerings)).toBe(40)
    expect(largestOfferingCapacity('s3', offerings)).toBeUndefined()
  })
})
