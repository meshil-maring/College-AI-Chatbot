/**
 * Phase 6.19 — Admin navigation model tests.
 *
 * The navigation model is UX-only, but it must NEVER drift into privilege:
 * these tests pin that the admin navigation exposes exactly the
 * server-verified admin surfaces and that every non-admin role (including
 * null/unknown) fails closed with an EMPTY navigation.
 */

/// <reference types="vitest/globals" />
import {
  ADMIN_NAV_ITEMS,
  ADMIN_VIEW_HEADINGS,
  buildAdminNavigation,
} from './adminNavigation.ts'

describe('buildAdminNavigation', () => {
  it('returns the admin navigation for the admin role', () => {
    const navigation = buildAdminNavigation('admin')
    expect(navigation.map((item) => item.key)).toEqual([
      'dashboard',
      'approvals',
      'staff-faculty',
      'students',
      'attendance',
      'results',
      'test-results',
      'notices',
      'documents',
      'faqs',
      'assistant',
      'profile',
      'permissions',
      'faculty-assignments',
    ])
  })

  it('shows the new administration views only with their server permissions', () => {
    expect(buildAdminNavigation('admin', ['permissions.read']).map((item) => item.key)).toEqual(['permissions'])
    expect(buildAdminNavigation('admin', ['faculty.assignments.manage']).map((item) => item.key)).toEqual(['faculty-assignments'])
  })

  it('returns an empty navigation for every other role (fail closed)', () => {
    expect(buildAdminNavigation('student')).toEqual([])
    expect(buildAdminNavigation('faculty')).toEqual([])
    expect(buildAdminNavigation('staff')).toEqual([])
    expect(buildAdminNavigation(null)).toEqual([])
    expect(buildAdminNavigation('unknown-role')).toEqual([])
  })

  it('filters admin navigation to the server-resolved permission set', () => {
    expect(
      buildAdminNavigation('admin', ['ai.chat', 'profile.own.read']).map((item) => item.key),
    ).toEqual(['assistant', 'profile'])
    expect(buildAdminNavigation('admin', [])).toEqual([])
  })

  it('contains no invented or unauthorized entries', () => {
    const labels = ADMIN_NAV_ITEMS.map((item) => item.label)
    expect(labels).toContain('Staff Permissions')
    expect(labels).toContain('Faculty Assignments')
    expect(labels).not.toContain('Institution Administration')
    expect(labels).not.toContain('Audit Logs')
    expect(labels).not.toContain('Learning Resources')
    // Every label is unique.
    expect(new Set(labels).size).toBe(labels.length)
  })
})

describe('ADMIN_VIEW_HEADINGS', () => {
  it('has a heading for every admin view', () => {
    for (const item of ADMIN_NAV_ITEMS) {
      expect(ADMIN_VIEW_HEADINGS[item.key]).toBeTruthy()
    }
  })
})
