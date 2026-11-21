import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../lib/queryClient.ts'
import {
  changeStaffPermissions,
  getDelegableStaffPermissions,
  getStaffPermissions,
  listMembershipRoster,
} from '../../../services/admin/adminApi.ts'
import { staffFacultyKeys } from '../staff-faculty/staffFacultyKeys.ts'

/** A roster click asking the permissions section to open one Staff member. */
export interface StaffPermissionFocus {
  userId: string
  requestedAt: number
}

function message(cause: unknown, fallback: string) {
  return cause instanceof Error ? cause.message : fallback
}

/**
 * Cached reads and the grant/revoke command for the Staff permissions section.
 * The reads share Staff and Faculty Management's cache scope, so a role change
 * there also refreshes who can be given permissions.
 */
export function useStaffPermissions(accessToken: string, focus: StaffPermissionFocus | null) {
  const membersQuery = useQuery(
    {
      queryKey: staffFacultyKeys.permissionMembers(accessToken),
      queryFn: async () => {
        const roster = await listMembershipRoster(accessToken, 'staff', 'active')
        return roster.members.flatMap((member) =>
          member.user_id === null ? [] : [{ user_id: member.user_id, name: member.name, email: member.email }],
        )
      },
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )
  const catalogueQuery = useQuery(
    {
      queryKey: staffFacultyKeys.delegablePermissions(accessToken),
      queryFn: () => getDelegableStaffPermissions(accessToken),
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )
  const members = membersQuery.data ?? []
  const [chosenUserId, setSelectedUserId] = useState('')
  // Fall back to the first active Staff member until one is chosen (or if the
  // chosen one is no longer Staff).
  const selectedUserId = members.some((member) => member.user_id === chosenUserId)
    ? chosenUserId
    : (members[0]?.user_id ?? '')
  const stateQuery = useQuery(
    {
      queryKey: staffFacultyKeys.staffPermissions(accessToken, selectedUserId),
      queryFn: () => getStaffPermissions(accessToken, selectedUserId),
      enabled: selectedUserId !== '',
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )
  const [selectedCodes, setSelectedCodes] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [actionError, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  // Open the Staff member chosen from the roster.
  useEffect(() => {
    if (focus === null) return
    setSelectedUserId(focus.userId)
    setSelectedCodes([])
    setNotice(null)
  }, [focus])

  // Only the first load hides the section. Switching member keeps the picker
  // visible; their permission list stays disabled until it arrives.
  const loading = membersQuery.isPending || catalogueQuery.isPending
  const loadError =
    membersQuery.error || catalogueQuery.error
      ? message(membersQuery.error ?? catalogueQuery.error, 'Could not load Staff permissions.')
      : stateQuery.error
        ? message(stateQuery.error, 'Could not load this Staff member.')
        : null

  async function apply(action: 'grant' | 'revoke') {
    if (!selectedUserId || selectedCodes.length === 0) return
    const verb = action === 'grant' ? 'Grant' : 'Revoke'
    if (!window.confirm(`${verb} ${selectedCodes.length} permission(s) for this Staff member?`)) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const result = await changeStaffPermissions(accessToken, selectedUserId, selectedCodes, action)
      queryClient.setQueryData(staffFacultyKeys.staffPermissions(accessToken, selectedUserId), result.permissions)
      setSelectedCodes([])
      setNotice(`${verb} completed. ${result.changed} permission grant(s) changed.`)
    } catch (cause) {
      setError(message(cause, `Could not ${verb.toLowerCase()} permissions.`))
    } finally {
      setBusy(false)
    }
  }

  return {
    members,
    selectedUserId,
    setSelectedUserId,
    state: stateQuery.data ?? null,
    catalogue: catalogueQuery.data ?? [],
    selectedCodes,
    setSelectedCodes,
    loading,
    busy,
    error: actionError ?? loadError,
    setError,
    notice,
    apply,
  }
}
