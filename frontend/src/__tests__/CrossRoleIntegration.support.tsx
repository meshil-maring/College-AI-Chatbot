import { screen, within } from '@testing-library/react'
import { beforeEach, vi } from 'vitest'
import { mockAllLoaded } from '../features/student/__tests__/studentTestFixtures.ts'
import * as adminApi from '../services/admin/adminApi.ts'
import { buildDashboardSummary } from '../test/adminDashboardFixtures.ts'
import type { DashboardSummary } from '../types/admin.ts'
import type { CurrentUser } from '../types/auth.ts'
vi.mock('../services/auth/devAuth.ts', () => ({
  fetchDevAuthStatus: vi.fn().mockResolvedValue({ dev_test_mode: false }),
}))

vi.mock('../services/admin/adminApi.ts')

vi.mock('../services/students/studentApi.ts', () => ({
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

vi.mock('../features/auth/session/AuthProvider.tsx', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => authState,
}))

export const INSTITUTION_A = '30000000-0000-0000-0000-000000000001'

export const INSTITUTION_B = '30000000-0000-0000-0000-000000000002'

/** Server-issued identities (auth_user_id comes from the JWT `sub`). */
export const ADMIN_A: CurrentUser = {
  authenticated: true,
  user_id: '11111111-1111-1111-1111-111111111111',
  auth_user_id: 'aaaaaaaa-0000-0000-0000-00000000000a',
  email: 'admin.a@college.edu',
  role: 'admin',
  institution_id: INSTITUTION_A,
}

export const ADMIN_B: CurrentUser = {
  authenticated: true,
  user_id: '11111111-1111-1111-1111-111111111112',
  auth_user_id: 'aaaaaaaa-0000-0000-0000-00000000000b',
  email: 'admin.b@college.edu',
  role: 'admin',
  institution_id: INSTITUTION_B,
}

export const STAFF_A: CurrentUser = {
  authenticated: true,
  user_id: '22222222-2222-2222-2222-222222222221',
  auth_user_id: 'bbbbbbbb-0000-0000-0000-00000000000a',
  email: 'staff.a@college.edu',
  role: 'staff',
  institution_id: INSTITUTION_A,
}

export const FACULTY_A: CurrentUser = {
  authenticated: true,
  user_id: '33333333-3333-3333-3333-333333333331',
  auth_user_id: 'cccccccc-0000-0000-0000-00000000000a',
  email: 'faculty.a@college.edu',
  role: 'faculty',
  institution_id: INSTITUTION_A,
}

export const STUDENT_B: CurrentUser = {
  authenticated: true,
  user_id: '44444444-4444-4444-4444-444444444442',
  auth_user_id: 'dddddddd-0000-0000-0000-00000000000b',
  email: 'student.b@college.edu',
  role: 'student',
  institution_id: INSTITUTION_B,
}

export const DASHBOARD_SUMMARY: DashboardSummary = buildDashboardSummary()

export const NAV_LANDMARKS: Readonly<Record<string, string>> = {
  admin: 'Admin navigation',
  staff: 'Staff navigation',
  faculty: 'Faculty navigation',
  student: 'Student navigation',
}

export const ROLES: Array<[string, CurrentUser]> = [
  ['admin', ADMIN_A],
  ['staff', STAFF_A],
  ['faculty', FACULTY_A],
  ['student', STUDENT_B],
]

/** Labels a shell must NEVER render, per authenticated role. */
export const FORBIDDEN_LABELS: Readonly<Record<string, readonly string[]>> = {
  student: ['Admin Panel', 'Student Approvals', 'Students', 'Test Results', 'Documents', 'FAQs', 'User Management'],
  faculty: [
    'Admin Panel',
    'Student Approvals',
    'Test Results',
    'Documents',
    'FAQs',
    'User Management',
    // Faculty Students uses authorized section rosters. Student self-service
    // and administrative endpoints retain their separate role boundaries.
  ],
  staff: ['Admin Panel', 'Test Results', 'Documents', 'FAQs', 'User Management'],
  // The admin shell manages attendance/results/notices, but never renders a
  // student-only surface such as "Learning Resources".
  admin: ['Learning Resources'],
}

export function setIdentity(user: CurrentUser | null, role: string | null, status: string = 'authenticated'): void {
  authState.status = status
  authState.user = user
  authState.role = role
}

export async function navigationLabels(role: string): Promise<string[]> {
  const nav = await screen.findByRole('navigation', { name: NAV_LANDMARKS[role] })
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

export { authState }
