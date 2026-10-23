import { describe, expect, it } from 'vitest'
import {
  FACULTY_COMING_SOON_VIEWS,
  FACULTY_NAV_ITEMS,
  FACULTY_VIEW_HEADINGS,
  buildFacultyNavigation,
} from './facultyNavigation.ts'

describe('faculty navigation after academic retirement', () => {
  it('keeps profile, chat and existing information placeholders', () => {
    expect(FACULTY_NAV_ITEMS.map((item) => item.key)).toEqual(['profile', 'notices', 'resources', 'assistant'])
    for (const item of FACULTY_NAV_ITEMS) expect(FACULTY_VIEW_HEADINGS[item.key]).toBeTruthy()
    expect(FACULTY_COMING_SOON_VIEWS).toEqual(['notices', 'resources'])
  })
  it.each(['student', 'staff', 'admin', 'super_admin', 'unknown', null])('rejects role %s', (role) => {
    expect(buildFacultyNavigation(role)).toEqual([])
  })
  it('ignores retired teaching grants and respects profile/chat grants', () => {
    expect(
      buildFacultyNavigation('faculty', ['attendance.read', 'faculty.assignments.manage']).map((item) => item.key),
    ).toEqual(['notices', 'resources'])
    expect(buildFacultyNavigation('faculty', ['ai.chat']).map((item) => item.key)).toEqual([
      'notices',
      'resources',
      'assistant',
    ])
  })
})
