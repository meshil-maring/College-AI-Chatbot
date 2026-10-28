import { useCallback, useEffect, useRef, useState } from 'react'
import {
  changeMembershipStatus,
  decideMembershipRequest,
  listMembershipRequests,
  listMembershipRoster,
} from '../../../services/admin/adminApi.ts'
import type { MembershipRequest, MembershipRole, MembershipRosterEntry } from '../../../types/admin.ts'

type RequestFilter = 'all' | MembershipRole | 'pending'

export function useStaffFacultyManagement(accessToken: string) {
  const [requestFilter, setRequestFilter] = useState<RequestFilter>('pending')
  const [requests, setRequests] = useState<MembershipRequest[]>([])
  const [members, setMembers] = useState<MembershipRosterEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [actionKey, setActionKey] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const identity = useRef(accessToken)
  identity.current = accessToken
  const loadGeneration = useRef(0)

  const load = useCallback(async () => {
    const generation = ++loadGeneration.current
    setLoading(true)
    setError(null)
    try {
      const role = requestFilter === 'staff' || requestFilter === 'faculty' ? requestFilter : undefined
      const status = requestFilter === 'pending' ? 'pending' : undefined
      const [requestData, rosterData] = await Promise.all([
        listMembershipRequests(accessToken, role, status),
        listMembershipRoster(accessToken),
      ])
      if (generation !== loadGeneration.current || identity.current !== accessToken) return
      setRequests(requestData.requests)
      setMembers(rosterData.members)
    } catch (cause) {
      if (generation !== loadGeneration.current || identity.current !== accessToken) return
      setError(cause instanceof Error ? cause.message : 'Could not load Staff & Faculty management.')
    } finally {
      if (generation === loadGeneration.current && identity.current === accessToken) setLoading(false)
    }
  }, [accessToken, requestFilter])
  const latestLoad = useRef(load)
  latestLoad.current = load

  useEffect(() => {
    void load()
    return () => {
      ++loadGeneration.current
    }
  }, [load])

  useEffect(() => {
    setRequests([])
    setMembers([])
    setActionKey(null)
    setSuccess(null)
  }, [accessToken])

  async function decide(request: MembershipRequest, decision: 'approve' | 'reject') {
    const retry = decision === 'approve' && request.status === 'approved'
    const action = retry ? 'Retry sign-in setup for' : decision === 'approve' ? 'Approve' : 'Reject'
    if (!window.confirm(`${action} ${request.full_name || request.email}?`)) return
    setActionKey(`${decision}:${request.request_id}`)
    setError(null)
    setSuccess(null)
    try {
      const result = await decideMembershipRequest(accessToken, request.request_id, decision)
      if (identity.current !== accessToken) return
      setSuccess(retry ? 'Sign-in setup completed. This account can now sign in.' : result.message)
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

  async function lifecycle(member: MembershipRosterEntry, action: 'deactivate' | 'reactivate') {
    if (!member.user_id) return
    if (!window.confirm(`${action === 'deactivate' ? 'Deactivate' : 'Reactivate'} ${member.name || member.email}?`))
      return
    setActionKey(`${action}:${member.user_id}`)
    setError(null)
    setSuccess(null)
    try {
      const result = await changeMembershipStatus(accessToken, member.user_id, action)
      if (identity.current !== accessToken) return
      setSuccess(result.message)
      await latestLoad.current()
    } catch (cause) {
      if (identity.current !== accessToken) return
      setError(cause instanceof Error ? cause.message : `Could not ${action} this member.`)
    } finally {
      if (identity.current === accessToken) setActionKey(null)
    }
  }

  return { requestFilter, setRequestFilter, requests, members, loading, actionKey, error, success, decide, lifecycle }
}
