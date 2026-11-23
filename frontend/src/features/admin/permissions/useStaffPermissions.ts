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
import { notification } from '../../../lib/notifications/notification.ts'

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
  // Boxes ticked or unticked since the last save: each flips that permission.
  const [changedCodes, setChangedCodes] = useState<ReadonlySet<string>>(new Set())
  // The list is read-only until the administrator chooses Edit.
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [actionError, setError] = useState<string | null>(null)

  // Open the Staff member chosen from the roster.
  useEffect(() => {
    if (focus === null) return
    setSelectedUserId(focus.userId)
    setChangedCodes(new Set())
    setEditing(false)
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

  function toggle(code: string) {
    setChangedCodes((previous) => {
      const next = new Set(previous)
      if (next.has(code)) next.delete(code)
      else next.add(code)
      return next
    })
  }

  function selectMember(userId: string) {
    setSelectedUserId(userId)
    setChangedCodes(new Set())
    setEditing(false)
    setError(null)
  }

  const isGranted = (code: string) =>
    (stateQuery.data?.permissions ?? []).some((item) => item.code === code && !item.inherited && item.direct_grant_id)
  const toGrant = [...changedCodes].filter((code) => !isGranted(code))
  const toRevoke = [...changedCodes].filter(isGranted)

  async function save() {
    if (!selectedUserId || changedCodes.size === 0) return
    const parts = [
      toGrant.length ? `grant ${toGrant.length}` : '',
      toRevoke.length ? `revoke ${toRevoke.length}` : '',
    ].filter(Boolean)
    if (!window.confirm(`Save changes for this Staff member: ${parts.join(' and ')} permission(s)?`)) return
    const stateKey = staffFacultyKeys.staffPermissions(accessToken, selectedUserId)
    setBusy(true)
    setError(null)
    let changed = 0
    try {
      for (const [action, codes] of [
        ['grant', toGrant],
        ['revoke', toRevoke],
      ] as const) {
        if (codes.length === 0) continue
        const result = await changeStaffPermissions(accessToken, selectedUserId, codes, action)
        // Record each step at once, so a failure in the next one keeps only
        // the changes that were not applied.
        queryClient.setQueryData(stateKey, result.permissions)
        setChangedCodes((previous) => new Set([...previous].filter((code) => !codes.includes(code))))
        changed += result.changed
      }
      setEditing(false)
      notification.success('Permissions updated successfully', `${changed} permission grant(s) changed.`)
    } catch (cause) {
      setError(message(cause, 'Could not save permission changes.'))
    } finally {
      setBusy(false)
    }
  }

  return {
    members,
    selectedUserId,
    selectMember,
    state: stateQuery.data ?? null,
    catalogue: catalogueQuery.data ?? [],
    changedCodes,
    toGrant,
    toRevoke,
    toggle,
    editing,
    startEditing: () => {
      setEditing(true)
      setError(null)
    },
    cancelEditing: () => {
      setChangedCodes(new Set())
      setEditing(false)
      setError(null)
    },
    loading,
    busy,
    error: actionError ?? loadError,
    save,
  }
}
