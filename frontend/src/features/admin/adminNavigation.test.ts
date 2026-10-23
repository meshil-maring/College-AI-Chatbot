import { describe, expect, it } from 'vitest'
import { ADMIN_NAV_ITEMS, ADMIN_VIEW_HEADINGS, buildAdminNavigation } from './adminNavigation.ts'

describe('administrator navigation after academic retirement', () => {
  it('contains account, knowledge and communication views', () => {
    expect(ADMIN_NAV_ITEMS.map((item) => item.key)).toEqual([
      'profile',
      'staff-faculty',
      'approvals',
      'notices',
      'documents',
      'faqs',
      'assistant',
      'permissions',
    ])
    for (const item of ADMIN_NAV_ITEMS) expect(ADMIN_VIEW_HEADINGS[item.key]).toBeTruthy()
  })
  it.each(['student', 'staff', 'faculty', 'super_admin', 'unknown', null])('rejects role %s', (role) => {
    expect(buildAdminNavigation(role)).toEqual([])
  })
  it('requires all account approval permissions and filters other views', () => {
    expect(buildAdminNavigation('admin', ['students.read', 'students.approve']).map((item) => item.key)).toEqual([])
    expect(
      buildAdminNavigation('admin', ['students.read', 'students.approve', 'students.reject']).map((item) => item.key),
    ).toEqual(['approvals'])
    expect(buildAdminNavigation('admin', ['ai.chat', 'profile.own.read']).map((item) => item.key)).toEqual([
      'profile',
      'assistant',
    ])
    expect(buildAdminNavigation('admin', [])).toEqual([])
  })
  it('cannot restore retired screens through old grants', () => {
    expect(
      buildAdminNavigation('admin', ['courses.read', 'attendance.read', 'results.read', 'faculty.assignments.manage']),
    ).toEqual([])
  })
})
