import { describe, expect, it } from 'vitest'
import { teachingState } from './facultyAssignmentUi.tsx'

describe('teaching status presentation follows authoritative half-open validity', () => {
  const start_at = '2026-10-09T09:00:00Z'
  const end_at = '2026-10-09T10:00:00Z'
  const assignment = { start_at, end_at, is_active: true, revoked_at: null }

  it('includes the start, excludes the end and distinguishes scheduling', () => {
    expect(teachingState(assignment, Date.parse(start_at) - 1)).toBe('scheduled')
    expect(teachingState(assignment, Date.parse(start_at))).toBe('active')
    expect(teachingState(assignment, Date.parse(end_at) - 1)).toBe('active')
    expect(teachingState(assignment, Date.parse(end_at))).toBe('expired')
  })

  it('gives revocation and disabled state priority', () => {
    expect(teachingState({ ...assignment, revoked_at: start_at, is_active: false }, Date.parse(start_at))).toBe('revoked')
    expect(teachingState({ ...assignment, is_active: false }, Date.parse(start_at))).toBe('disabled')
  })

  it('uses assigned_at for legacy records and fails closed on missing or invalid validity', () => {
    expect(teachingState({ assigned_at: start_at }, Date.parse(start_at))).toBe('active')
    for (const row of [{}, { start_at: 'invalid' }, { start_at: '2026-10-09T09:00' }, { start_at, end_at: 'invalid' }, { start_at, end_at: start_at }]) expect(teachingState(row, Date.parse(start_at))).toBe('unavailable')
  })
})
