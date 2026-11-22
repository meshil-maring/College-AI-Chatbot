import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../../lib/queryClient.ts'
import {
  cancelInstitutionAdminInvitation,
  inviteInstitutionAdmin,
  listInstitutionAdmins,
  revokeInstitutionAdmin,
  setInstitutionAdminAccess,
  transferInstitutionOwnership,
} from '../../../../services/admin/adminApi.ts'
import type { AdminAccessArea, AdminInvitation, InstitutionAdmin } from '../../../../types/admin/administrators.ts'
import { staffFacultyKeys } from '../staffFacultyKeys.ts'

function message(cause: unknown, fallback: string) {
  return cause instanceof Error ? cause.message : fallback
}

/**
 * Institution administrators, the Owner and pending administrator invitations.
 * Only the Owner may change them; the server enforces that on every command.
 * Results from an earlier session are ignored.
 */
export function useInstitutionAdmins(accessToken: string) {
  const query = useQuery(
    {
      queryKey: staffFacultyKeys.administrators(accessToken),
      queryFn: () => listInstitutionAdmins(accessToken),
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )
  const [actionKey, setActionKey] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const identity = useRef(accessToken)
  identity.current = accessToken

  useEffect(() => {
    setActionKey(null)
    setNotice(null)
    setError(null)
  }, [accessToken])

  /** Runs one command; returns an error message, or null when it succeeded. */
  async function run(key: string, work: () => Promise<{ message: string }>, failure: string) {
    setActionKey(key)
    setNotice(null)
    setError(null)
    try {
      const result = await work()
      if (identity.current !== accessToken) return null
      setNotice(result.message)
      return null
    } catch (cause) {
      if (identity.current !== accessToken) return null
      const reason = message(cause, failure)
      setError(reason)
      return reason
    } finally {
      if (identity.current === accessToken) {
        await queryClient.invalidateQueries({ queryKey: staffFacultyKeys.administrators(accessToken) })
        setActionKey(null)
      }
    }
  }

  const invite = (email: string, fullName: string, accessAreas: AdminAccessArea[] | null) =>
    run(
      'invite',
      () =>
        inviteInstitutionAdmin(accessToken, {
          email: email.trim().toLowerCase(),
          full_name: fullName.trim() || null,
          access_areas: accessAreas,
        }),
      'The invitation could not be sent.',
    )

  const setAccess = (admin: InstitutionAdmin, accessAreas: AdminAccessArea[] | null) =>
    run(
      `access:${admin.user_id}`,
      () => setInstitutionAdminAccess(accessToken, admin.user_id, accessAreas),
      'Access could not be changed.',
    )

  const cancel = (invitation: AdminInvitation) =>
    window.confirm(`Cancel the administrator invitation for ${invitation.email}?`)
      ? run(
          `cancel:${invitation.invitation_id}`,
          () => cancelInstitutionAdminInvitation(accessToken, invitation.invitation_id),
          'The invitation could not be cancelled.',
        )
      : Promise.resolve(null)

  const revoke = (admin: InstitutionAdmin) =>
    window.confirm(`Remove ${admin.name}'s administrator access? Their account and records are kept.`)
      ? run(
          `revoke:${admin.user_id}`,
          () => revokeInstitutionAdmin(accessToken, admin.user_id),
          'Could not remove access.',
        )
      : Promise.resolve(null)

  const transfer = (admin: InstitutionAdmin) =>
    window.confirm(
      `Make ${admin.name} the Owner? You will remain an administrator but can no longer manage administrators.`,
    )
      ? run(
          `owner:${admin.user_id}`,
          () => transferInstitutionOwnership(accessToken, admin.user_id),
          'Ownership could not be transferred.',
        )
      : Promise.resolve(null)

  return {
    administrators: query.data?.administrators ?? [],
    invitations: query.data?.invitations ?? [],
    viewerIsOwner: query.data?.viewer_is_owner ?? false,
    loading: query.isPending,
    loadError: query.error ? message(query.error, 'Could not load administrators.') : null,
    actionKey,
    notice,
    error,
    dismiss: () => {
      setNotice(null)
      setError(null)
    },
    invite,
    setAccess,
    cancel,
    revoke,
    transfer,
  }
}

export type InstitutionAdminsModel = ReturnType<typeof useInstitutionAdmins>
