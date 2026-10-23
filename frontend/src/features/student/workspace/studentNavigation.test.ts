import { describe, expect, it } from 'vitest'
import { STUDENT_NAV_ITEMS, buildStudentNavigation } from './studentNavigation.ts'

describe('student navigation after academic retirement', () => {
  it('contains identity and institution information only', () => {
    expect(STUDENT_NAV_ITEMS.map((item) => item.key)).toEqual(['profile', 'notices', 'resources', 'assistant'])
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
})
