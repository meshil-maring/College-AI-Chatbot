import { describe, expect, it } from 'vitest'
import { STUDENT_NAV_ITEMS, buildStudentNavigation } from './studentNavigation.ts'

describe('student navigation', () => {
  it('includes semester registration alongside account and institution information', () => {
    expect(STUDENT_NAV_ITEMS.map((item) => item.key)).toEqual([
      'dashboard',
      'profile',
      'registration',
      'transfer-requests',
      'notifications',
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
  it('shows the dashboard only to students who can read their profile', () => {
    expect(buildStudentNavigation('student', ['profile.own.read']).map((item) => item.key)).toEqual([
      'dashboard',
      'profile',
    ])
    expect(buildStudentNavigation('staff', ['profile.own.read']).map((item) => item.key)).toEqual(['profile'])
  })
  it('shows registration only to students with the current read grant', () => {
    expect(buildStudentNavigation('student', ['registration.own.read']).map((item) => item.key)).toEqual([
      'registration',
    ])
    expect(buildStudentNavigation('staff', ['registration.own.read'])).toEqual([])
    expect(buildStudentNavigation('faculty', ['registration.own.read'])).toEqual([])
  })
  it('shows transfer requests to students who can read their own transfers', () => {
    expect(buildStudentNavigation('student', ['transfers.read']).map((item) => item.key)).toEqual(['transfer-requests'])
    expect(buildStudentNavigation('student', ['transfers.request'])).toEqual([])
    expect(buildStudentNavigation('faculty', ['transfers.read'])).toEqual([])
  })
})
