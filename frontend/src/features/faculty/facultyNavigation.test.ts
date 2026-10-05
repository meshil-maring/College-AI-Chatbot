/**
 * Phase 6.17 — Faculty navigation model tests.
 *
 * The navigation model is UX-only, but it must NEVER drift into privilege:
 * these tests pin that the faculty navigation exposes exactly the
 * server-verified faculty surfaces and never an administrative or
 * student-academic entry.
 */

/// <reference types="vitest/globals" />
import {
  FACULTY_NAV_ITEMS,
  FACULTY_VIEW_HEADINGS,
  FACULTY_WORKSPACE_SURFACES,
  buildFacultyNavigation,
} from './facultyNavigation.ts'

describe('buildFacultyNavigation', () => {
  it('returns the faculty navigation for the faculty role', () => {
    const navigation = buildFacultyNavigation('faculty')
    expect(navigation).toEqual([
      { key: 'dashboard', label: 'Dashboard' },
      { key: 'assistant', label: 'AI Assistant' },
      { key: 'profile', label: 'Profile' },
      { key: 'assignments', label: 'My Sections' },
    ])
  })

  it('contains no admin navigation', () => {
    const labels = FACULTY_NAV_ITEMS.map((item) => item.label)
    expect(labels).not.toContain('Admin Panel')
    expect(labels).not.toContain('User Management')
    expect(labels).not.toContain('Role Management')
    expect(labels).not.toContain('Institution Administration')
    expect(labels).not.toContain('Students')
  })

  it('returns an empty navigation for every other role (fail safe)', () => {
    expect(buildFacultyNavigation('student')).toEqual([])
    expect(buildFacultyNavigation('staff')).toEqual([])
    expect(buildFacultyNavigation('admin')).toEqual([])
    expect(buildFacultyNavigation(null)).toEqual([])
    expect(buildFacultyNavigation('unknown-role')).toEqual([])
  })

  it('requires the server-resolved assignment permission to show My Sections', () => {
    const navigation = buildFacultyNavigation('faculty', ['ai.chat'])
    expect(navigation.map((item) => item.key)).not.toContain('assignments')
    expect(buildFacultyNavigation('faculty', ['ai.chat', 'faculty.assignments.read'])
      .map((item) => item.key)).toContain('assignments')
  })
})

describe('FACULTY_VIEW_HEADINGS', () => {
  it('has a heading for every faculty view', () => {
    for (const item of FACULTY_NAV_ITEMS) {
      expect(FACULTY_VIEW_HEADINGS[item.key]).toBeTruthy()
    }
  })
})

describe('FACULTY_WORKSPACE_SURFACES (verified capability map)', () => {
  it('marks the AI Assistant and active assignment list as available', () => {
    const available = FACULTY_WORKSPACE_SURFACES.filter(
      (surface) => surface.status === 'available',
    )
    expect(available.map((surface) => surface.key)).toEqual(['assignments', 'assistant'])
  })

  it('marks student academic surfaces as not available (server-denied)', () => {
    const notAvailable = FACULTY_WORKSPACE_SURFACES.filter(
      (surface) => surface.status === 'not-available',
    )
    expect(notAvailable.map((surface) => surface.key).sort()).toEqual([
      'attendance',
      'notices',
      'resources',
      'results',
      'students',
    ])
  })
})
