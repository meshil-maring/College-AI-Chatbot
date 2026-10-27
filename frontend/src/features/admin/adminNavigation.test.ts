import { describe, expect, it } from 'vitest'
import { ADMIN_NAV_ITEMS, ADMIN_VIEW_HEADINGS, buildAdminNavigation } from './adminNavigation.ts'

describe('administrator navigation with approved Academic Setup', () => {
  it('contains account, knowledge and communication views', () => {
    expect(ADMIN_NAV_ITEMS.map((item) => item.key)).toEqual([
      'profile',
      'academic-setup',
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
    expect(buildAdminNavigation('admin', ['students.read', 'students.approve']).map((item) => item.key)).toEqual([
      'academic-setup',
    ])
    expect(
      buildAdminNavigation('admin', ['students.read', 'students.approve', 'students.reject']).map((item) => item.key),
    ).toEqual(['academic-setup', 'approvals'])
    expect(buildAdminNavigation('admin', ['ai.chat', 'profile.own.read']).map((item) => item.key)).toEqual([
      'profile',
      'academic-setup',
      'assistant',
    ])
    expect(buildAdminNavigation('admin', []).map((item) => item.key)).toEqual(['academic-setup'])
  })
  it('cannot restore retired screens through old grants', () => {
    expect(
      buildAdminNavigation('admin', ['attendance.read', 'results.read', 'faculty.assignments.manage']).map(
        (item) => item.key,
      ),
    ).toEqual(['academic-setup'])
  })
  it.each(['departments.read', 'academic_years.read', 'semesters.read', 'courses.read'])(
    'shows setup for %s alone',
    (permission) => {
      expect(buildAdminNavigation('admin', [permission]).map((item) => item.key)).toEqual(['academic-setup'])
    },
  )
  it('keeps the design overview visible with only management grants', () => {
    expect(buildAdminNavigation('admin', ['departments.manage']).map((item) => item.key)).toEqual(['academic-setup'])
  })
})
