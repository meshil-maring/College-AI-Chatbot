import { useState } from 'react'
import { useApiQuery } from '../../../../hooks/useApiQuery.ts'
import { notification } from '../../../../lib/notifications/notification.ts'
import {
  listStudentInvitations,
  reassignStudentInvitation,
  resendStudentInvitation,
} from '../../../../services/admin/students.ts'
import { invitationKey, refreshStudentInvitations } from './studentInvitationQueries.ts'

/** Pending setup invitations with resend and section-change actions; results are reported as toasts. */
export function useStudentInvitations(accessToken: string, identity: string, enabled: boolean) {
  const query = useApiQuery(invitationKey(identity), () => listStudentInvitations(accessToken), enabled, {
    cache: 'navigation',
  })
  const [busy, setBusy] = useState(false)
  const invitations = query.data?.invitations ?? []

  async function resend(invitationId: string) {
    setBusy(true)
    try {
      const result = await resendStudentInvitation(accessToken, invitationId)
      if (result.delivery_status === 'failed') notification.warning(result.delivery_message)
      else notification.success(result.delivery_message)
      refreshStudentInvitations(identity)
    } catch (reason) {
      notification.error(reason instanceof Error ? reason.message : 'A new setup link could not be sent.')
    } finally {
      setBusy(false)
    }
  }

  async function reassign(invitationId: string, sectionId: string) {
    if (!sectionId) return
    setBusy(true)
    try {
      await reassignStudentInvitation(accessToken, invitationId, sectionId)
      notification.success('Invitation section updated successfully')
      refreshStudentInvitations(identity)
    } catch (reason) {
      notification.error(reason instanceof Error ? reason.message : 'Section assignment could not be updated.')
    } finally {
      setBusy(false)
    }
  }

  return {
    invitations,
    loading: query.isPending,
    fetching: query.isFetching,
    error: query.error instanceof Error ? query.error.message : '',
    busy,
    refetch: () => void query.refetch(),
    resend,
    reassign,
  }
}
