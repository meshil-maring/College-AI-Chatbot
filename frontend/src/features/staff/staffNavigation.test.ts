import { describe, expect, it } from 'vitest'
import { STAFF_NAV_ITEMS, STAFF_VIEW_HEADINGS, buildStaffNavigation } from './staffNavigation.ts'

describe('staff navigation after academic retirement', () => {
  it('keeps profile, account approvals and chat', () => {
    expect(STAFF_NAV_ITEMS.map((item) => item.key)).toEqual(['profile', 'approvals', 'assistant'])
    for (const item of STAFF_NAV_ITEMS) expect(STAFF_VIEW_HEADINGS[item.key]).toBeTruthy()
  })
  it.each(['student', 'faculty', 'admin', 'super_admin', 'unknown', null])('rejects role %s', (role) => {
    expect(buildStaffNavigation(role)).toEqual([])
  })
  it('requires the account approval grant', () => {
    expect(buildStaffNavigation('staff', ['students.read']).map((item) => item.key)).toEqual([])
    expect(buildStaffNavigation('staff', ['students.approve']).map((item) => item.key)).toEqual(['approvals'])
    expect(buildStaffNavigation('staff', ['courses.read', 'attendance.read'])).toEqual([])
  })
})
