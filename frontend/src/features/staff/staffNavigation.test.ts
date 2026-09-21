/**
 * Phase 6.18 — Staff navigation model tests.
 *
 * The navigation model is UX-only, but it must NEVER drift into privilege:
 * these tests pin that the staff navigation exposes exactly the
 * server-verified staff surfaces and never an administrative or
 * student-academic entry.
 */

/// <reference types="vitest/globals" />
import {
  STAFF_NAV_ITEMS,
  STAFF_VIEW_HEADINGS,
  STAFF_WORKSPACE_SURFACES,
  buildStaffNavigation,
} from './staffNavigation.ts'

describe('buildStaffNavigation', () => {
  it('returns the staff navigation for the staff role', () => {
    const navigation = buildStaffNavigation('staff')
    expect(navigation).toEqual([
      { key: 'dashboard', label: 'Dashboard' },
      { key: 'approvals', label: 'Student Approvals' },
      { key: 'assistant', label: 'AI Assistant' },
      { key: 'profile', label: 'Profile' },
    ])
  })

  it('contains no admin navigation', () => {
    const labels = STAFF_NAV_ITEMS.map((item) => item.label)
    expect(labels).not.toContain('Admin Panel')
    expect(labels).not.toContain('User Management')
    expect(labels).not.toContain('Role Management')
    expect(labels).not.toContain('Institution Administration')
    expect(labels).not.toContain('Notices Management')
    expect(labels).not.toContain('Document Management')
  })

  it('returns an empty navigation for every other role (fail closed)', () => {
    expect(buildStaffNavigation('student')).toEqual([])
    expect(buildStaffNavigation('faculty')).toEqual([])
    expect(buildStaffNavigation('admin')).toEqual([])
    expect(buildStaffNavigation(null)).toEqual([])
    expect(buildStaffNavigation('unknown-role')).toEqual([])
  })
})

describe('STAFF_VIEW_HEADINGS', () => {
  it('has a heading for every staff view', () => {
    for (const item of STAFF_NAV_ITEMS) {
      expect(STAFF_VIEW_HEADINGS[item.key]).toBeTruthy()
    }
  })
})

describe('STAFF_WORKSPACE_SURFACES (verified capability map)', () => {
  it('marks only verified staff capabilities as available', () => {
    const available = STAFF_WORKSPACE_SURFACES.filter(
      (surface) => surface.status === 'available',
    )
    expect(available.map((surface) => surface.key).sort()).toEqual([
      'approvals',
      'assistant',
    ])
  })

  it('marks admin-only surfaces as not available (server-denied)', () => {
    const notAvailable = STAFF_WORKSPACE_SURFACES.filter(
      (surface) => surface.status === 'not-available',
    )
    expect(notAvailable.map((surface) => surface.key).sort()).toEqual([
      'attendance',
      'documents',
      'notices',
      'resources',
      'results',
      'students',
      'test-results',
      'user-management',
    ])
  })
})
