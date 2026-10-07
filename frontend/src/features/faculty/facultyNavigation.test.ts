/**
 * Faculty navigation model tests.
 *
 * The navigation model is UX-only, but it must NEVER drift into privilege:
 * these tests pin that the faculty navigation exposes exactly the
 * server-verified faculty surfaces plus the inert "Coming Soon"
 * placeholders — and never an administrative entry. The placeholders are
 * additionally pinned as inert (no capability key, no data contract).
 */

/// <reference types="vitest/globals" />
import {
  FACULTY_COMING_SOON_VIEWS,
  FACULTY_NAV_ITEMS,
  FACULTY_VIEW_HEADINGS,
  FACULTY_WORKSPACE_SURFACES,
  buildFacultyNavigation,
} from './facultyNavigation.ts'

describe('buildFacultyNavigation', () => {
  it('requires a results grant from teaching role or scoped responsibility', () => {
    expect(buildFacultyNavigation('faculty', []).map(item => item.key)).not.toContain('results')
    expect(buildFacultyNavigation('faculty', ['results.read']).map(item => item.key)).toContain('results')
    expect(buildFacultyNavigation('faculty', [], ['results.read']).map(item => item.key)).toContain('results')
    expect(FACULTY_COMING_SOON_VIEWS).not.toContain('results')
  })
  it('returns the faculty navigation for the faculty role', () => {
    const navigation = buildFacultyNavigation('faculty')
    expect(navigation).toEqual([
      { key: 'dashboard', label: 'Dashboard' },
      { key: 'assignments', label: 'My Sections' },
      { key: 'students', label: 'Students' },
      { key: 'attendance', label: 'Attendance' },
      { key: 'results', label: 'Results' },
      { key: 'notices', label: 'Notices' },
      { key: 'resources', label: 'Learning Resources' },
      { key: 'assistant', label: 'AI Assistant' },
      { key: 'profile', label: 'Profile' },
    ])
  })

  it('contains no admin navigation', () => {
    const labels = FACULTY_NAV_ITEMS.map((item) => item.label)
    expect(labels).not.toContain('Admin Panel')
    expect(labels).not.toContain('User Management')
    expect(labels).not.toContain('Role Management')
    expect(labels).not.toContain('Institution Administration')
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

  it('keeps the inert Coming Soon placeholders even with no capability grants', () => {
    // Placeholders expose no backend capability, so there is nothing to
    // permission-check; they are roadmap labels for any faculty identity.
    const navigation = buildFacultyNavigation('faculty', [])
    const keys = navigation.map((item) => item.key)
    expect(keys).toEqual(['students', 'notices', 'resources'])
  })
})

describe('FACULTY_VIEW_HEADINGS', () => {
  it('has a heading for every faculty view', () => {
    for (const item of FACULTY_NAV_ITEMS) {
      expect(FACULTY_VIEW_HEADINGS[item.key]).toBeTruthy()
    }
  })
})

describe('FACULTY_COMING_SOON_VIEWS (inert placeholders)', () => {
  it('covers exactly the sections with no backend contract', () => {
    expect([...FACULTY_COMING_SOON_VIEWS].sort()).toEqual([
      'notices',
      'resources',
      'students',
    ])
  })

  it('every Coming Soon view has a navigation entry and a heading', () => {
    const navKeys = FACULTY_NAV_ITEMS.map((item) => item.key)
    for (const view of FACULTY_COMING_SOON_VIEWS) {
      expect(navKeys).toContain(view)
      expect(FACULTY_VIEW_HEADINGS[view]).toBeTruthy()
    }
  })

  it('never overlaps a verified capability view', () => {
    expect(FACULTY_COMING_SOON_VIEWS).not.toContain('dashboard')
    expect(FACULTY_COMING_SOON_VIEWS).not.toContain('assignments')
    expect(FACULTY_COMING_SOON_VIEWS).not.toContain('assistant')
    expect(FACULTY_COMING_SOON_VIEWS).not.toContain('profile')
  })
})

describe('FACULTY_WORKSPACE_SURFACES (verified capability map)', () => {
  it('marks the AI Assistant and active assignment list as available', () => {
    const available = FACULTY_WORKSPACE_SURFACES.filter(
      (surface) => surface.status === 'available',
    )
    expect(available.map((surface) => surface.key)).toEqual(['assignments', 'assistant', 'attendance', 'results'])
  })

  it('marks student academic surfaces as not available (server-denied)', () => {
    const notAvailable = FACULTY_WORKSPACE_SURFACES.filter(
      (surface) => surface.status === 'not-available',
    )
    expect(notAvailable.map((surface) => surface.key).sort()).toEqual([
      'notices',
      'resources',
      'students',
    ])
  })
})
