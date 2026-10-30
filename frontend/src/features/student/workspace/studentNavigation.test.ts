import { describe, expect, it } from 'vitest'
import { STUDENT_NAV_ITEMS, buildStudentNavigation } from './studentNavigation.ts'

describe('student navigation', () => {
  it('includes semester registration alongside account and institution information', () => {
    expect(STUDENT_NAV_ITEMS.map((item) => item.key)).toEqual([
      'profile',
      'registration',
      'notices',
      'resources',
      'assistant',
    ])
  })
  it.each(['admin', 'super_admin', 'unknown', null])('rejects role %s', (role) => {
    expect(buildStudentNavigation(role)).toEqual([])
  })
  it('filters by current grants and ignores retired academic grants', () => {
    expect(
      buildStudentNavigation('student', ['results.own.read', 'attendance.own.read', 'ai.chat']).map((item) => item.key),
    ).toEqual(['assistant'])
    expect(buildStudentNavigation('student', [])).toEqual([])
  })
  it('shows registration only to students with the current read grant', () => {
    expect(buildStudentNavigation('student', ['registration.own.read']).map((item) => item.key)).toEqual([
      'registration',
    ])
    expect(buildStudentNavigation('staff', ['registration.own.read'])).toEqual([])
    expect(buildStudentNavigation('faculty', ['registration.own.read'])).toEqual([])
  })
})
