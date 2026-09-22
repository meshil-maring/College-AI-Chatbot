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
      'students',
      'attendance',
      'results',
      'test-results',
      'notices',
      'documents',
      'faqs',
      'assistant',
      'profile',
    ])
  })

  it('returns an empty navigation for every other role (fail closed)', () => {
    expect(buildAdminNavigation('student')).toEqual([])
    expect(buildAdminNavigation('faculty')).toEqual([])
    expect(buildAdminNavigation('staff')).toEqual([])
    expect(buildAdminNavigation(null)).toEqual([])
    expect(buildAdminNavigation('unknown-role')).toEqual([])
  })

  it('contains no invented or unauthorized entries', () => {
    const labels = ADMIN_NAV_ITEMS.map((item) => item.label)
    // No speculative administrative surfaces (no frontend manager exists).
    expect(labels).not.toContain('User Management')
    expect(labels).not.toContain('Role Management')
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