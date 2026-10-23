import { beforeEach, vi } from 'vitest'
import * as adminApi from '../../../services/admin/adminApi.ts'

vi.mock('../../../services/admin/adminApi.ts')
vi.mock('../../chat/ChatShell.tsx', () => ({ default: () => <div>AI Assistant chat</div> }))
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
vi.mock('../../auth/session/AuthProvider.tsx', () => ({ useAuth: () => authState }))
beforeEach(() => {
  authState.role = 'admin'
  authState.accessToken = 'test-token'
  authState.logout.mockReset()
  authState.user.effective_permissions = ['*']
  vi.mocked(adminApi.getAdminIdentity).mockReset()
  vi.mocked(adminApi.listPendingStudents).mockReset().mockResolvedValue([])
})
export { authState }
