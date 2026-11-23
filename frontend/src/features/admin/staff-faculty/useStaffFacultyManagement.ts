import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../lib/queryClient.ts'
import {
  changeMembershipStatus,
  decideMembershipRequest,
  listMembershipRequests,
  listMembershipRoster,
  setMemberDepartment,
  setMemberRole,
} from '../../../services/admin/adminApi.ts'
import { getAcademicSetup } from '../../../services/admin/academics.ts'
import type { MembershipRequest, MembershipRole, MembershipRosterEntry } from '../../../types/admin.ts'
import { getDepartmentHeads } from '../../../services/students/transferApi.ts'
import { roleLabel } from './StaffFacultyUI.tsx'
import { useDepartmentHeadActions } from './useDepartmentHeadActions.ts'
import { staffFacultyKeys, type RequestFilter } from './staffFacultyKeys.ts'
import { notification } from '../../../lib/notifications/notification.ts'

function message(cause: unknown, fallback: string) {
  return cause instanceof Error ? cause.message : fallback
}

// Confirmation text for each account status change.
const LIFECYCLE_PROMPTS = {
  deactivate: (name: string) => `Deactivate ${name}? They lose access; their records are kept.`,
  reactivate: (name: string) => `Reactivate ${name}?`,
  suspend: (name: string) => `Suspend ${name}? They cannot sign in until reactivated.`,
}

export function useStaffFacultyManagement(accessToken: string) {
  const [requestFilter, setRequestFilter] = useState<RequestFilter>('pending')
  const [actionKey, setActionKey] = useState<string | null>(null)
  const [actionError, setError] = useState<string | null>(null)
  const identity = useRef(accessToken)
  identity.current = accessToken

  // Cached reads: returning to this page shows saved data at once and only
  // refreshes it in the background when it is over a minute old.
  const requestsQuery = useQuery(
    {
      queryKey: staffFacultyKeys.requests(accessToken, requestFilter),
      queryFn: () =>
        listMembershipRequests(
          accessToken,
          requestFilter === 'staff' || requestFilter === 'faculty' ? requestFilter : undefined,
          requestFilter === 'pending' ? 'pending' : undefined,
        ),
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )
  // Pending requests for the summary, whichever filter is open. With the
  // default Pending filter this is the same cached query, so no extra request.
  const pendingQuery = useQuery(
    {
      queryKey: staffFacultyKeys.requests(accessToken, 'pending'),
      queryFn: () => listMembershipRequests(accessToken, undefined, 'pending'),
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )
  const rosterQuery = useQuery(
    {
      queryKey: staffFacultyKeys.roster(accessToken),
      queryFn: () => listMembershipRoster(accessToken),
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )
  // Active departments from Academic Setup; the administrator assigns one to each member.
  const departmentsQuery = useQuery(
    {
      queryKey: staffFacultyKeys.departments(accessToken),
      queryFn: async () => {
        const catalogue = await getAcademicSetup(accessToken)
        const active = (catalogue.records.departments ?? []).filter((department) => department.is_active)
        return [...active].sort((a, b) => a.name.localeCompare(b.name))
      },
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )
  // Current Heads of Department, so the roster can show and change HOD appointments.
  const headsQuery = useQuery(
    {
      queryKey: staffFacultyKeys.heads(accessToken),
      queryFn: () => getDepartmentHeads(accessToken),
      ...NAVIGATION_QUERY_POLICY,
    },
    queryClient,
  )

  const requests = requestsQuery.data?.requests ?? []
  const members = rosterQuery.data?.members ?? []
  const departments = departmentsQuery.data ?? []
  const heads = headsQuery.data?.heads ?? []
  // Only a first load shows "Loading…"; background refreshes keep the saved lists.
  const loading = requestsQuery.isPending || rosterQuery.isPending
  const loadError =
    requestsQuery.error || rosterQuery.error
      ? message(requestsQuery.error ?? rosterQuery.error, 'Could not load Staff and Faculty management.')
      : departmentsQuery.isError
        ? 'Could not load departments. Add or check them in Academic Setup.'
        : null
  const error = actionError ?? loadError
  const pendingCount = pendingQuery.data?.requests.length ?? null

  function dismiss() {
    setError(null)
  }

  /** Refresh every read on this page after a change, and wait for it. */
  const latestLoad = useRef(() => queryClient.invalidateQueries({ queryKey: staffFacultyKeys.all(accessToken) }))
  latestLoad.current = () => queryClient.invalidateQueries({ queryKey: staffFacultyKeys.all(accessToken) })

  useEffect(() => {
    setActionKey(null)
    setError(null)
  }, [accessToken])

  async function decide(
    request: MembershipRequest,
    decision: 'approve' | 'reject',
    departmentId?: string,
    role?: MembershipRole,
  ) {
    const retry = decision === 'approve' && request.status === 'approved'
    const action = retry ? 'Retry sign-in setup for' : decision === 'approve' ? 'Approve' : 'Reject'
    const as = decision === 'approve' && !retry && role ? ` as ${roleLabel(role)}` : ''
    if (!window.confirm(`${action} ${request.full_name || request.email}${as}?`)) return
    setActionKey(`${decision}:${request.request_id}`)
    setError(null)
    try {
      const result = await decideMembershipRequest(accessToken, request.request_id, decision, departmentId, role)
      if (identity.current !== accessToken) return
      if (retry) notification.success('Sign-in setup completed', 'This account can now sign in.')
      else notification.success(result.message)
      await latestLoad.current()
    } catch (cause) {
      if (identity.current !== accessToken) return
      // Approval may have committed before provider confirmation failed.
      // Reload so the recorded decision and its retry action are reachable.
      await latestLoad.current()
      if (identity.current !== accessToken) return
      setError(cause instanceof Error ? cause.message : `Could not ${decision} this request.`)
    } finally {
      if (identity.current === accessToken) setActionKey(null)
    }
  }

  async function lifecycle(member: MembershipRosterEntry, action: 'deactivate' | 'reactivate' | 'suspend') {
    if (!member.user_id) return
    if (!window.confirm(LIFECYCLE_PROMPTS[action](member.name || member.email))) return
    setActionKey(`${action}:${member.user_id}`)
    setError(null)
    try {
      const result = await changeMembershipStatus(accessToken, member.user_id, action)
      if (identity.current !== accessToken) return
      notification.success(result.message)
      await latestLoad.current()
    } catch (cause) {
      if (identity.current !== accessToken) return
      setError(cause instanceof Error ? cause.message : `Could not ${action} this member.`)
    } finally {
      if (identity.current === accessToken) setActionKey(null)
    }
  }

  /** Run one roster action: show its result, reload, and ignore late replies from an old session. */
  async function runAction(key: string, work: () => Promise<string>, failure: string) {
    setActionKey(key)
    setError(null)
    try {
      const message = await work()
      if (identity.current !== accessToken) return
      notification.success(message)
      await latestLoad.current()
    } catch (cause) {
      if (identity.current !== accessToken) return
      setError(cause instanceof Error ? cause.message : failure)
    } finally {
      if (identity.current === accessToken) setActionKey(null)
    }
  }

  async function changeRole(member: MembershipRosterEntry, role: MembershipRole) {
    if (!member.user_id || role === member.role) return
    const label = roleLabel(role)
    if (!window.confirm(`Change ${member.name || member.email} to ${label}? They will need to sign in again.`)) return
    await runAction(
      `role:${member.user_id}`,
      async () => (await setMemberRole(accessToken, member.user_id, role)).message,
      'Could not change the role.',
    )
  }

  async function changeDepartment(member: MembershipRosterEntry, departmentId: string) {
    const department = departments.find((item) => item.department_id === departmentId)
    if (!member.user_id || !department || departmentId === member.department_id) return
    if (!window.confirm(`Move ${member.name || member.email} to ${department.name}?`)) return
    await runAction(
      `department:${member.user_id}`,
      async () => (await setMemberDepartment(accessToken, member.user_id, departmentId)).message,
      'Could not change the department.',
    )
  }

  const allowMultiHod = headsQuery.data?.allow_multi_department_hod ?? true
  const hod = useDepartmentHeadActions({ accessToken, heads, departments, allowMultiHod, runAction })

  return {
    requestFilter,
    setRequestFilter,
    requests,
    members,
    departments,
    loading,
    actionKey,
    error,
    dismiss,
    pendingCount,
    // People, not appointments: one HOD may head several departments.
    headCount: new Set(heads.map((head) => head.faculty_user_id)).size,
    decide,
    lifecycle,
    notify: (message: string) => notification.success(message),
    changeDepartment,
    changeRole,
    ...hod,
  }
}
