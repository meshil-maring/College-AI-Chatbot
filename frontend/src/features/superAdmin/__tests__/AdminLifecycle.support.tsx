import { cleanup } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, vi } from 'vitest'
import type { AdminRoster, PlatformAuditPage } from '../../../types/platform.ts'
const rosterSpy = vi.hoisted(() => vi.fn())

const createInvitationSpy = vi.hoisted(() => vi.fn())

const cancelInvitationSpy = vi.hoisted(() => vi.fn())

const resendInvitationSpy = vi.hoisted(() => vi.fn())

const revokeAdminSpy = vi.hoisted(() => vi.fn())

const auditSpy = vi.hoisted(() => vi.fn())

const PlatformInstitutionError = vi.hoisted(
  () =>
    class extends Error {
      readonly status: number
      constructor(status: number, message: string) {
        super(message)
        this.status = status
      }
    },
)

vi.mock('../../../services/platform/platformInstitutionsApi.ts', () => ({
  PlatformInstitutionError,
  getAdminRoster: rosterSpy,
  createInvitation: createInvitationSpy,
  cancelInvitation: cancelInvitationSpy,
  resendInvitation: resendInvitationSpy,
  revokeInstitutionAdmin: revokeAdminSpy,
  listPlatformAudit: auditSpy,
}))

vi.mock('../../auth/session/AuthProvider.tsx', () => ({
  useAuth: () => ({ accessToken: 'session-token' }),
}))

export function Wrapper({ children }: { children: ReactNode }) {
  return <>{children}</>
}

export const ROSTER: AdminRoster = {
  institution_id: 'inst-1',
  admin_count: 1,
  admins: [
    {
      email: 'dean@unico.example',
      kind: 'admin',
      status: 'active',
      user_id: 'user-1',
      invitation_id: null,
      institution_id: 'inst-1',
      expires_at: null,
    },
  ],
  pending_invitations: [
    {
      email: 'owner@unico.example',
      kind: 'invitation',
      status: 'invited',
      user_id: null,
      invitation_id: 'inv-1',
      institution_id: 'inst-1',
      email_delivery_status: 'sent',
      email_delivery_attempts: 1,
      email_verified: false,
      resend_count: 0,
      expires_at: '2099-01-01T00:00:00+00:00',
    },
  ],
}

export const AUDIT_PAGE: PlatformAuditPage = {
  total: 1,
  limit: 25,
  offset: 0,
  entries: [
    {
      audit_id: 'audit-1',
      actor_user_id: 'user-9',
      actor_email: 'root@platform.test',
      action: 'institution_admin_invited',
      institution_id: 'inst-1',
      institution_name: 'Unico University',
      target_user_id: null,
      result: 'success',
      details: {},
      performed_at: '2026-10-01T00:00:00+00:00',
    },
  ],
}

beforeEach(() => {
  rosterSpy.mockResolvedValue(ROSTER)
  auditSpy.mockResolvedValue(AUDIT_PAGE)
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

export {
  auditSpy,
  cancelInvitationSpy,
  createInvitationSpy,
  PlatformInstitutionError,
  resendInvitationSpy,
  revokeAdminSpy,
  rosterSpy,
}
