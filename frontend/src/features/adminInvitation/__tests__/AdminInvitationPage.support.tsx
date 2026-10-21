import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'
const inspectSpy = vi.hoisted(() => vi.fn())

const acceptSpy = vi.hoisted(() => vi.fn())

const membershipSpy = vi.hoisted(() => vi.fn())

const recoverSpy = vi.hoisted(() => vi.fn())

const authState = vi.hoisted(() => ({
  status: 'unauthenticated',
  accessToken: null as string | null,
  user: null as { email: string } | null,
}))

vi.mock('../../auth/session/AuthProvider.tsx', () => ({ useAuth: () => authState }))

vi.mock('../../../services/invitations/adminInvitationApi.ts', () => ({
  AdminInvitationError: class extends Error {
    readonly status: number
    readonly code: string | null
    readonly isTerminal: boolean
    constructor(status: number, message: string, code: string | null = null) {
      super(message)
      this.status = status
      this.code = code
      this.isTerminal =
        code === 'INVITATION_EXPIRED' || code === 'INVITATION_CANCELLED' || code === 'INVITATION_ALREADY_ACCEPTED'
    }
  },
  inspectInvitation: inspectSpy,
  acceptInvitation: acceptSpy,
  acceptMembership: membershipSpy,
  recoverInvitationAccount: recoverSpy,
}))

export const TOKEN = 'a'.repeat(64)

export const INVITATION = {
  status: 'invited',
  institution_name: 'Unico University',
  institution_code: 'UNICO',
  email: 'dean@unico.example',
  expires_at: '2099-01-01T00:00:00+00:00',
  email_verified: false,
}

export const ACCEPTED = {
  institution_id: 'inst-1',
  institution_name: 'Unico University',
  email: 'dean@unico.example',
  role: 'admin',
  scope: 'institution',
  message: 'Your University Admin account is ready.',
}

export const PASSWORD = 'correct-horse-battery'

beforeEach(() => {
  authState.status = 'unauthenticated'
  authState.accessToken = null
  authState.user = null
  inspectSpy.mockResolvedValue(INVITATION)
  recoverSpy.mockReset()
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

export { acceptSpy, authState, inspectSpy, membershipSpy, recoverSpy }
