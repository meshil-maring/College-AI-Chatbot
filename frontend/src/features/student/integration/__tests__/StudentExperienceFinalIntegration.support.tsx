import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, vi } from 'vitest'
import { resetSessionExpiredListeners } from '../../../../services/shared/sessionEvents.ts'
const holder = vi.hoisted(() => ({ actual: {} as typeof import('../../../../services/students/studentApi.ts') }))
const { logoutMock } = vi.hoisted(() => ({ logoutMock: vi.fn() }))
vi.mock('../../../chat/ChatShell.tsx', () => ({ default: () => <div data-testid="chat-shell-mock">AI chat</div> }))
vi.mock('../../../auth/session/AuthProvider.tsx', () => ({
  useAuth: () => ({
    user: { email: 'student@college.edu' },
    role: 'student',
    accessToken: 'test-token',
    logout: logoutMock,
  }),
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))
vi.mock('../../../../services/students/studentApi.ts', async () => {
  const actual = await vi.importActual<typeof import('../../../../services/students/studentApi.ts')>(
    '../../../../services/students/studentApi.ts',
  )
  holder.actual = actual
  return { ...actual, getMyProfile: vi.fn(), getMyNotices: vi.fn(), getMyResources: vi.fn() }
})
export const nav = () => screen.getByRole('navigation', { name: 'Student navigation' })
export const goTo = async (user: ReturnType<typeof userEvent.setup>, label: string): Promise<void> => {
  await user.click(within(nav()).getByRole('button', { name: label }))
}
/** Students land on the dashboard; open Profile and wait for the identity card. */
export const openProfile = async (user: ReturnType<typeof userEvent.setup>): Promise<void> => {
  await screen.findByRole('heading', { name: /^Good (morning|afternoon|evening)/, level: 1 })
  await goTo(user, 'Profile')
  await screen.findByText('Welcome, REG-100')
}
beforeEach(() => {
  vi.resetAllMocks()
  resetSessionExpiredListeners()
  logoutMock.mockReset()
})
afterEach(() => {
  vi.unstubAllGlobals()
  resetSessionExpiredListeners()
})
export { holder, logoutMock }
