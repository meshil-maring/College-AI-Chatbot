import type { StudentInvitation } from '../../../../types/admin/students.ts'

export type InvitationFilter = 'all' | 'sent' | 'failed' | 'expired'
export type InvitationState = 'sent' | 'failed' | 'pending' | 'expired'

/** Expiry takes precedence: an expired link cannot be used even if its email was delivered. */
export function invitationState(invitation: StudentInvitation, now = Date.now()): InvitationState {
  if (new Date(invitation.expires_at).getTime() <= now) return 'expired'
  return invitation.email_delivery_status
}

export const STATE_LABELS: Record<InvitationState, string> = {
  sent: 'Sent',
  failed: 'Needs retry',
  pending: 'Sending',
  expired: 'Link expired',
}

export function countInvitations(invitations: StudentInvitation[], now = Date.now()) {
  const counts: Record<InvitationFilter, number> = { all: invitations.length, sent: 0, failed: 0, expired: 0 }
  invitations.forEach((invitation) => {
    const state = invitationState(invitation, now)
    if (state !== 'pending') counts[state] += 1
  })
  return counts
}

/** Match name, email, register/roll number, batch or section, then the chosen status. */
export function filterInvitations(
  invitations: StudentInvitation[],
  search: string,
  filter: InvitationFilter,
  now = Date.now(),
) {
  const term = search.trim().toLowerCase()
  return invitations.filter((invitation) => {
    if (filter !== 'all' && invitationState(invitation, now) !== filter) return false
    if (!term) return true
    return [
      invitation.student_name,
      invitation.email,
      invitation.register_number,
      invitation.university_roll_number,
      invitation.batch_code,
      invitation.batch_name,
      invitation.section_code,
      invitation.section_name,
    ].some((value) => value?.toLowerCase().includes(term))
  })
}
