import { beforeEach, vi } from 'vitest'
vi.mock('../../../../services/auth/devAuth.ts', async () => {
  const actual = await vi.importActual<typeof import('../../../../services/auth/devAuth.ts')>('../../../../services/auth/devAuth.ts')
  return { ...actual, fetchDevAuthStatus: vi.fn() }
})

/** Mutable auth context mock so each test can drive status/error/login. */
const authState = vi.hoisted(() => ({
  status: 'unauthenticated' as string,
  user: null,
  accessToken: null,
  error: null as string | null,
  login: vi.fn<(identifier: string, password: string, institutionCode?: string) => Promise<void>>(),
  logout: vi.fn(),
}))

vi.mock('../../session/AuthProvider.tsx', () => ({
  useAuth: () => authState,
}))

vi.mock('../../../../services/registration/registration.ts', async () => ({
  ...(await vi.importActual<typeof import('../../../../services/registration/registration.ts')>('../../../../services/registration/registration.ts')),
  lookupInstitution: vi.fn(),
  registerStudent: vi.fn(),
}))

beforeEach(() => {
  authState.status = 'unauthenticated'
  authState.error = null
  authState.login.mockReset()
  authState.login.mockResolvedValue(undefined)
})

export { authState }
