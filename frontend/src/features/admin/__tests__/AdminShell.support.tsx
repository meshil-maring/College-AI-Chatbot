import { beforeEach, vi } from 'vitest'
import * as adminApi from '../../../services/admin/adminApi.ts'
import { adminStudentWorkspaceApi as studentApi } from '../../../services/admin/adminStudentWorkspaceApi.ts'
import { emptyDashboardSummary } from '../../../test/adminDashboardFixtures.ts'
import type { DashboardSummary } from '../../../types/admin.ts'
vi.mock('../../../services/admin/adminApi.ts')

vi.mock('../../../services/admin/adminStudentWorkspaceApi.ts')

vi.mock('../../chat/ChatShell.tsx', () => ({ default: () => <div>AI Assistant chat</div> }))

export const DASHBOARD_SUMMARY: DashboardSummary = emptyDashboardSummary()

/** Mutable auth context so each test can drive the canonical role. */
const authState = vi.hoisted(() => ({
  status: 'authenticated',
  user: {
    authenticated: true,
    user_id: 'u1',
    auth_user_id: 'a1',
    email: 'admin@test.com',
    role: 'admin' as const,
    institution_id: 'inst-1',
    effective_permissions: ['*'] as string[],
  },
  role: 'admin' as string | null,
  accessToken: 'test-token' as string | null,
  logout: vi.fn(),
}))

vi.mock('../../auth/session/AuthProvider.tsx', () => ({
  useAuth: () => authState,
}))

beforeEach(() => {
  authState.role = 'admin'
  authState.accessToken = 'test-token'
  authState.logout.mockReset()
  authState.user.effective_permissions = ['*']
  vi.mocked(adminApi.getAdminIdentity).mockReset()
  vi.mocked(adminApi.getDashboardSummary).mockReset()
  vi.mocked(adminApi.getDashboardSummary).mockResolvedValue(DASHBOARD_SUMMARY)
  vi.mocked(studentApi.getSections).mockResolvedValue([
    {
      can_manage: true,
      assignment_id: 'section-1',
      assigned_at: '',
      section_id: 'section-1',
      academic_year_id: 'year-1',
      semester_id: 'semester-1',
      section: {
        section_id: 'section-1',
        name: 'Section A',
        code: 'A',
        program_id: 'program-1',
        program: { program_id: 'program-1', name: 'Computer Science', degree_type: 'B.Tech' },
        course: { name: 'Data Mining', code: 'CS501' },
      },
    },
  ])
  vi.mocked(studentApi.getStudents).mockResolvedValue({ items: [], total: 0 })
  vi.mocked(studentApi.getRegistrations).mockResolvedValue({ items: [], total: 0 })
  vi.mocked(studentApi.getBatches).mockResolvedValue([])
  vi.mocked(studentApi.getHistory).mockResolvedValue({ items: [], total: 0 })
})

export { authState }
