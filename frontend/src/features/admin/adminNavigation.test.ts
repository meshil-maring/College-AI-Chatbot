import { describe, expect, it } from 'vitest'
import { ADMIN_NAV_ITEMS, ADMIN_VIEW_HEADINGS, buildAdminNavigation } from './adminNavigation.ts'

describe('administrator navigation with approved Academic Setup', () => {
  it('contains account, knowledge and communication views', () => {
    expect(ADMIN_NAV_ITEMS.map((item) => item.key)).toEqual([
      'academic-setup',
      'approvals',
      'staff-faculty',
      'notices',
      'documents',
      'faqs',
      'assistant',
      'profile',
    ])
    expect([...new Set(ADMIN_NAV_ITEMS.map((item) => item.group))]).toEqual([
      'Academics',
      'People',
      'Communication',
      'Assistant',
      'Account',
    ])
    for (const item of ADMIN_NAV_ITEMS) expect(ADMIN_VIEW_HEADINGS[item.key]).toBeTruthy()
  })
  it('names the merged page Staff and Faculty Management with no separate permissions page', () => {
    expect(ADMIN_NAV_ITEMS.find((item) => item.key === 'staff-faculty')?.label).toBe('Staff and Faculty Management')
    expect(ADMIN_NAV_ITEMS.some((item) => item.label === 'Staff Permissions')).toBe(false)
  })
  it.each(['student', 'staff', 'faculty', 'super_admin', 'unknown', null])('rejects role %s', (role) => {
    expect(buildAdminNavigation(role)).toEqual([])
  })
  it('shows student management to readers and leaves workflow actions permission-gated', () => {
    expect(buildAdminNavigation('admin', ['students.read']).map((item) => item.key)).toEqual([
      'academic-setup',
      'approvals',
    ])
    expect(
      buildAdminNavigation('admin', ['students.read', 'students.approve', 'students.reject']).map((item) => item.key),
    ).toEqual(['academic-setup', 'approvals'])
    expect(buildAdminNavigation('admin', ['ai.chat', 'profile.own.read']).map((item) => item.key)).toEqual([
      'academic-setup',
      'assistant',
      'profile',
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
