import { describe, expect, it } from 'vitest'
import { emptyDraft, toInvitation, validateStep } from './memberDraft.ts'

const basics = {
  full_name: ' Ada   Lovelace ',
  email: ' Ada@Example.com ',
  employee_id: 'EMP-1',
  designation: 'Professor',
  joining_date: '2026-07-01',
}

describe('memberDraft', () => {
  it('keeps defaults when known details are undefined', () => {
    const draft = emptyDraft({ employee_id: undefined, email: 'a@b.co' })
    expect(draft.employee_id).toBe('')
    expect(draft.email).toBe('a@b.co')
  })

  it('validates employee IDs and phone numbers like the server', () => {
    for (const employee_id of ['EMP 1', '-EMP', 'E'.repeat(41), '']) {
      expect(validateStep(0, emptyDraft({ ...basics, employee_id })).employee_id).toBeDefined()
    }
    expect(validateStep(0, emptyDraft({ ...basics, phone: 'call me' })).phone).toBeDefined()
    expect(validateStep(0, emptyDraft(basics))).toEqual({})
  })

  it('checks experience only for faculty and within 0 to 70 years', () => {
    const base = { ...basics, department_id: 'd1', employment_start_date: '2026-07-01' }
    expect(validateStep(1, emptyDraft({ ...base, experience_years: '71' })).experience_years).toBeDefined()
    expect(validateStep(1, emptyDraft({ ...base, experience_years: '6.5' }))).toEqual({})
  })

  it('drops the contract end for permanent work and the primary from additional departments', () => {
    const request = toInvitation(
      emptyDraft({
        ...basics,
        department_id: 'd1',
        additional_department_ids: ['d1', 'd2'],
        employment_start_date: '2026-07-01',
        contract_end_date: '2027-01-01',
        experience_years: '6.5',
      }),
    )
    expect(request.full_name).toBe('Ada Lovelace')
    expect(request.email).toBe('ada@example.com')
    expect(request.additional_department_ids).toEqual(['d2'])
    expect(request.profile.faculty?.contract_end_date).toBeNull()
    expect(request.profile.faculty?.experience_years).toBe(6.5)
    expect(request.profile.staff).toBeUndefined()
  })
})
