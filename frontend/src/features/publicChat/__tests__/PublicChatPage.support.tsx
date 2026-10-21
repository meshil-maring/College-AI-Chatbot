import { vi } from 'vitest'

vi.mock('../../../services/chat/publicChat.ts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../services/chat/publicChat.ts')>()
  return { ...actual, publicChat: vi.fn() }
})

export const authProviderSpy = vi.fn(({ children }: { children: React.ReactNode }) => <>{children}</>)

vi.mock('../../auth/session/AuthProvider.tsx', () => ({
  AuthProvider: (props: { children: React.ReactNode }) => authProviderSpy(props),
  useAuth: () => {
    throw new Error('Public chat must not use authentication')
  },
}))

vi.mock('../../../services/auth/devAuth.ts', () => ({
  fetchDevAuthStatus: vi.fn().mockResolvedValue({ dev_test_mode: false }),
}))
