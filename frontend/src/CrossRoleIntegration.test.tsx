/**
 * Phase 6.20 — Cross-role integration & authorization boundary validation.
 *
 * PURPOSE: the Phase 6.16–6.19 suites each prove ONE role's experience in
 * isolation. This suite proves the INTEGRATION between them, at the App
 * boundary, from the single input that decides everything: the
 * server-authoritative role in AuthProvider state (`/auth/me` -> `user.role`).
 *
 * Covered here (frontend half of the phase; the backend half lives in
 * `backend/tests/test_cross_role_integration_phase_6_20.py`):
 *   1. role -> shell mapping for admin / staff / faculty / student + the
 *      fail-safe unsupported (null / unknown) state;
 *   2. role -> navigation mapping, compared against each role's navigation
 *      model (the UX mirror of the server authorization matrix);
 *   3. role transitions: no previous role's shell, navigation, cached data or
 *      in-shell view state may survive an authentication replacement — this
 *      includes the SAME role with a DIFFERENT account/tenant (the
 *      cross-tenant case the backend isolates);
 *   4. logout -> login as another role;
 *   5. no cross-role DOM leakage and no access-token exposure.
 *
 * The session lifecycle itself (restore / expiry / multi-tab) is covered by
 * `CrossRoleSessionLifecycle.test.tsx`, which runs the REAL AuthProvider.
 *
 * No new role capability is created here: this file asserts the existing
 * boundaries only. Navigation is UX ONLY — every endpoint re-authorizes the
 * caller server-side.
 */

/// <reference types="vitest/globals" />
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App.tsx'
import { ADMIN_NAV_ITEMS } from './features/admin/adminNavigation.ts'
import { FACULTY_NAV_ITEMS } from './features/faculty/facultyNavigation.ts'
import { STAFF_NAV_ITEMS } from './features/staff/staffNavigation.ts'
import { STUDENT_NAV_ITEMS } from './features/student/studentNavigation.ts'
import { mockAllLoaded } from './features/student/studentTestFixtures.ts'
import * as adminApi from './services/adminApi.ts'
import type { CurrentUser } from './types/auth.ts'
import type { DashboardSummary } from './types/admin.ts'

vi.mock('./services/devAuth.ts', () => ({
  fetchDevAuthStatus: vi.fn().mockResolvedValue({ dev_test_mode: false }),
}))

vi.mock('./services/adminApi.ts')
vi.mock('./services/studentApi.ts', () => ({
  StudentApiError: class StudentApiError extends Error {
    readonly status = 0
    readonly code: string | null = null
  },
  getMyAcademicProfile: vi.fn(),
  getMyAttendanceSummary: vi.fn(),
  getMyResultsSummary: vi.fn(),
  getMyTestResultsSummary: vi.fn(),
  getMyNotices: vi.fn(),
  getMyResources: vi.fn(),
}))

/**
 * Mutable auth context. The mock returns the live object, so a test can change
 * role/identity between renders and drive the App boundary directly — exactly
 * what a real /auth/me response doing so would do.
 */
const authState = vi.hoisted(() => ({
  status: 'authenticated' as string,
  user: null as unknown,
  role: null as string | null,
  accessToken: 'cross-role-token' as string | null,
  error: null as string | null,
  login: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('./features/auth/AuthProvider.tsx', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => authState,
}))

const INSTITUTION_A = '30000000-0000-0000-0000-000000000001'
const INSTITUTION_B = '30000000-0000-0000-0000-000000000002'

/** Server-issued identities (auth_user_id comes from the JWT `sub`). */
const ADMIN_A: CurrentUser = {
  authenticated: true,
  user_id: '11111111-1111-1111-1111-111111111111',
  auth_user_id: 'aaaaaaaa-0000-0000-0000-00000000000a',
  email: 'admin.a@college.edu',
  role: 'admin',
  institution_id: INSTITUTION_A,
}

const ADMIN_B: CurrentUser = {
  authenticated: true,
  user_id: '11111111-1111-1111-1111-111111111112',
  auth_user_id: 'aaaaaaaa-0000-0000-0000-00000000000b',
  email: 'admin.b@college.edu',
  role: 'admin',
  institution_id: INSTITUTION_B,
}

const STAFF_A: CurrentUser = {
  authenticated: true,
  user_id: '22222222-2222-2222-2222-222222222221',
  auth_user_id: 'bbbbbbbb-0000-0000-0000-00000000000a',
  email: 'staff.a@college.edu',
  role: 'staff',
  institution_id: INSTITUTION_A,
}

const FACULTY_A: CurrentUser = {
  authenticated: true,
  user_id: '33333333-3333-3333-3333-333333333331',
  auth_user_id: 'cccccccc-0000-0000-0000-00000000000a',
  email: 'faculty.a@college.edu',
  role: 'faculty',
  institution_id: INSTITUTION_A,
}

const STUDENT_B: CurrentUser = {
  authenticated: true,
  user_id: '44444444-4444-4444-4444-444444444442',
  auth_user_id: 'dddddddd-0000-0000-0000-00000000000b',
  email: 'student.b@college.edu',
  role: 'student',
  institution_id: INSTITUTION_B,
}

const DASHBOARD_SUMMARY: DashboardSummary = {
  counts: {
    knowledge_sources: 3,
    documents: 5,
    faqs: 2,
    notices: 4,
    students: 120,
    student_results: 60,
    test_results: 40,
    attendance_records: 800,
  },
  recent_audit: [],
}

const NAV_LANDMARKS: Readonly<Record<string, string>> = {
  admin: 'Admin navigation',
  staff: 'Staff navigation',
  faculty: 'Faculty navigation',
  student: 'Student navigation',
}

const ROLES: Array<[string, CurrentUser]> = [
  ['admin', ADMIN_A],
  ['staff', STAFF_A],
  ['faculty', FACULTY_A],
  ['student', STUDENT_B],
]

/** Labels a shell must NEVER render, per authenticated role. */
const FORBIDDEN_LABELS: Readonly<Record<string, readonly string[]>> = {
  student: [
    'Admin Panel',
    'Student Approvals',
    'Students',
    'Test Results',
    'Documents',
    'FAQs',
    'User Management',
  ],
  faculty: [
    'Admin Panel',
    'Student Approvals',
    'Students',
    'Test Results',
    'Documents',
    'FAQs',
    'User Management',
  ],
  staff: [
    'Admin Panel',
    'Students',
    'Test Results',
    'Documents',
    'FAQs',
    'User Management',
  ],
  // The admin shell manages attendance/results/notices, but never renders a
  // student-only surface such as "Learning Resources".
  admin: ['Learning Resources'],
}

function setIdentity(
  user: CurrentUser | null,
  role: string | null,
  status: string = 'authenticated',
): void {
  authState.status = status
  authState.user = user
  authState.role = role
}

function navigationLabels(role: string): string[] {
  const nav = screen.getByRole('navigation', { name: NAV_LANDMARKS[role] })
  return within(nav)
    .getAllByRole('button')
    .map((button) => button.textContent ?? '')
}

beforeEach(() => {
  authState.accessToken = 'cross-role-token'
  authState.error = null
  authState.login.mockReset()
  authState.logout.mockReset()
  setIdentity(ADMIN_A, 'admin')

  vi.mocked(adminApi.getDashboardSummary).mockReset()
  vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(DASHBOARD_SUMMARY)
  vi.mocked(adminApi.listKnowledgeSources).mockReset()
  vi.mocked(adminApi.listKnowledgeSources).mockResolvedValue([])
  vi.mocked(adminApi.listPendingStudents).mockReset()
  vi.mocked(adminApi.listPendingStudents).mockResolvedValue([])
  mockAllLoaded()
})


describe('role -> shell matrix', () => {
  it('renders AdminShell for the admin role only', () => {
    render(<App />)
    expect(screen.getByText('Admin Panel')).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Admin navigation' })).toBeInTheDocument()
    for (const other of ['staff', 'faculty', 'student']) {
      expect(
        screen.queryByRole('navigation', { name: NAV_LANDMARKS[other] }),
      ).not.toBeInTheDocument()
    }
  })

  it('renders StaffShell for the staff role only', () => {
    setIdentity(STAFF_A, 'staff')
    render(<App />)
    expect(screen.getByRole('navigation', { name: 'Staff navigation' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('navigation', { name: 'Student navigation' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('navigation', { name: 'Faculty navigation' }),
    ).not.toBeInTheDocument()
  })

  it('renders FacultyShell for the faculty role only', () => {
    setIdentity(FACULTY_A, 'faculty')
    render(<App />)
    expect(screen.getByRole('navigation', { name: 'Faculty navigation' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('navigation', { name: 'Student navigation' }),
    ).not.toBeInTheDocument()
  })

  it('renders StudentShell for the student role only', () => {
    setIdentity(STUDENT_B, 'student')
    render(<App />)
    expect(screen.getByRole('navigation', { name: 'Student navigation' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('navigation', { name: 'Staff navigation' }),
    ).not.toBeInTheDocument()
  })

  it('fails safe for a null and an unknown role: no shell, no navigation, sign-out only', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<App />)

    // An AUTHENTICATED account whose /auth/me role resolves to null (no
    // supported role) and an unknown role value both fail closed.
    for (const role of [null, 'unknown-role'] as const) {
      setIdentity(null, role)
      rerender(<App />)
      expect(screen.getByText('Access restricted')).toBeInTheDocument()
      for (const landmark of Object.values(NAV_LANDMARKS)) {
        expect(screen.queryByRole('navigation', { name: landmark })).not.toBeInTheDocument()
      }
      expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    }

    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(authState.logout).toHaveBeenCalledTimes(1)
  })
})


describe('role -> navigation isolation', () => {
  it('renders exactly its own navigation model for each role', () => {
    const { rerender } = render(<App />)

    expect(navigationLabels('admin')).toEqual(ADMIN_NAV_ITEMS.map((item) => item.label))

    setIdentity(STAFF_A, 'staff')
    rerender(<App />)
    expect(navigationLabels('staff')).toEqual(STAFF_NAV_ITEMS.map((item) => item.label))

    setIdentity(FACULTY_A, 'faculty')
    rerender(<App />)
    expect(navigationLabels('faculty')).toEqual(FACULTY_NAV_ITEMS.map((item) => item.label))

    setIdentity(STUDENT_B, 'student')
    rerender(<App />)
    expect(navigationLabels('student')).toEqual(STUDENT_NAV_ITEMS.map((item) => item.label))
  })

  it('never exposes another role\'s navigation entries', () => {
    const { rerender } = render(<App />)

    for (const [role, user] of ROLES) {
      setIdentity(user, role)
      rerender(<App />)
      const labels = navigationLabels(role)
      for (const forbidden of FORBIDDEN_LABELS[role]) {
        expect(labels, `${role} navigation must not expose "${forbidden}"`).not.toContain(
          forbidden,
        )
      }
    }
  })

  it('keeps the staff approval exception and nothing more for staff', () => {
    setIdentity(STAFF_A, 'staff')
    render(<App />)
    const labels = navigationLabels('staff')
    expect(labels).toContain('Student Approvals')
    for (const adminOnly of ['Students', 'Test Results', 'Documents', 'FAQs']) {
      expect(labels).not.toContain(adminOnly)
    }
  })
})

describe('role transition safety', () => {
  it('admin -> student leaves no admin shell, navigation, or dashboard state', async () => {
    const { rerender } = render(<App />)
    expect(await screen.findByText('Overview')).toBeInTheDocument()

    setIdentity(STUDENT_B, 'student')
    rerender(<App />)

    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Admin navigation' })).not.toBeInTheDocument()
    expect(screen.queryByText('Overview')).not.toBeInTheDocument()
    expect(screen.queryByText('Recent Activity')).not.toBeInTheDocument()
    expect(screen.queryByText('Signed in as admin.a@college.edu')).not.toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Student navigation' })).toBeInTheDocument()
  })

  it('walks every transition without inheriting the previous role', () => {
    const { rerender } = render(<App />)

    for (const [role, user] of ROLES) {
      setIdentity(user, role)
      rerender(<App />)
      expect(screen.getByRole('navigation', { name: NAV_LANDMARKS[role] })).toBeInTheDocument()
      for (const other of Object.keys(NAV_LANDMARKS)) {
        if (other === role) continue
        expect(
          screen.queryByRole('navigation', { name: NAV_LANDMARKS[other] }),
        ).not.toBeInTheDocument()
      }
      // Only the current identity is rendered.
      expect(screen.getByText(`Signed in as ${user.email}`)).toBeInTheDocument()
      for (const forbidden of FORBIDDEN_LABELS[role]) {
        expect(navigationLabels(role)).not.toContain(forbidden)
      }
    }
  })

  it('logout then login as another role never resurrects the previous shell', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<App />)
    expect(screen.getByText('Admin Panel')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(authState.logout).toHaveBeenCalledTimes(1)

    // The (real) AuthProvider clears the session on logout: status becomes
    // unauthenticated, so only the login form is rendered.
    setIdentity(null, null, 'unauthenticated')
    rerender(<App />)
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()

    // A different account signs in: the student shell, with no admin residue.
    setIdentity(STUDENT_B, 'student')
    rerender(<App />)
    expect(screen.getByRole('navigation', { name: 'Student navigation' })).toBeInTheDocument()
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument()
  })
})


describe('stale view-state protection', () => {
  it('resets an admin view when the SAME role is replaced by another account', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<App />)

    await user.click(screen.getByRole('button', { name: 'Documents' }))
    expect(screen.getByRole('heading', { level: 1, name: 'Documents' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Documents' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByText('Signed in as admin.a@college.edu')).toBeInTheDocument()

    // Same role, DIFFERENT account/tenant — the status never leaves
    // 'authenticated', so only the identity-scoped shell key can discard
    // tenant A's view state and already-fetched admin data.
    setIdentity(ADMIN_B, 'admin')
    rerender(<App />)

    expect(screen.getByRole('button', { name: 'Dashboard' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(
      screen.queryByRole('heading', { level: 1, name: 'Documents' }),
    ).not.toBeInTheDocument()
    expect(screen.queryByText('Signed in as admin.a@college.edu')).not.toBeInTheDocument()
    expect(screen.getByText('Signed in as admin.b@college.edu')).toBeInTheDocument()
  })

  it('resets a staff approval view before a student session mounts', async () => {
    const user = userEvent.setup()
    setIdentity(STAFF_A, 'staff')
    const { rerender } = render(<App />)

    await user.click(screen.getByRole('button', { name: 'Student Approvals' }))
    expect(await screen.findByRole('heading', { name: 'Student Approvals' })).toBeInTheDocument()

    setIdentity(STUDENT_B, 'student')
    rerender(<App />)

    expect(screen.queryByRole('heading', { name: 'Student Approvals' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Student Approvals' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Dashboard' })).toHaveAttribute(
      'aria-current',
      'page',
    )
  })
})

describe('no token exposure', () => {
  it('never renders the access token or internal identifiers for any role', () => {
    const { rerender } = render(<App />)

    for (const [role, user] of ROLES) {
      setIdentity(user, role)
      rerender(<App />)
      expect(document.body.innerHTML, role).not.toContain('cross-role-token')
      expect(screen.queryByText('cross-role-token')).not.toBeInTheDocument()
      expect(document.body.innerHTML, role).not.toContain(user.auth_user_id)
    }
  })
})

