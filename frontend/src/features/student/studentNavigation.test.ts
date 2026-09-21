/**
 * Phase 6.16 — Student navigation tests (UX only, never authorization).
 *
 * Verifies the student shell exposes exactly the seven student surfaces and
 * never an administrative entry, for every role that renders the shell — and
 * renders NOTHING for roles that must not see the shell at all.
 */

import { describe, expect, it } from 'vitest'
import { STUDENT_NAV_ITEMS, buildStudentNavigation } from './studentNavigation.ts'

const EXPECTED = ['dashboard', 'attendance', 'results', 'notices', 'resources', 'assistant', 'profile']

const PRIVILEGED = ['admin', 'staff management', 'student management', 'role management', 'institution management']

describe('student navigation', () => {
  it('contains exactly the seven student surfaces in order', () => {
    expect(STUDENT_NAV_ITEMS.map((item) => item.key)).toEqual(EXPECTED)
  })

  it('contains no privileged entries for any shell role', () => {
    for (const role of ['student', 'staff', 'faculty']) {
      const labels = buildStudentNavigation(role).map((item) => item.label.toLowerCase())
      for (const forbidden of PRIVILEGED) {
        expect(labels).not.toContain(forbidden)
      }
    }
  })

  it('grants the same navigation to student, staff, and faculty', () => {
    expect(buildStudentNavigation('staff')).toEqual(buildStudentNavigation('student'))
    expect(buildStudentNavigation('faculty')).toEqual(buildStudentNavigation('student'))
  })

  it('returns an empty navigation for admin, unknown, and null roles', () => {
    expect(buildStudentNavigation('admin')).toEqual([])
    expect(buildStudentNavigation('unknown-role')).toEqual([])
    expect(buildStudentNavigation(null)).toEqual([])
  })
})
