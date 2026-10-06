import { useCallback, useEffect, useState } from 'react'
import {
  changeMembershipStatus,
  decideMembershipRequest,
  listMembershipRequests,
  listMembershipRoster,
} from '../../services/adminApi.ts'
import type {
  MembershipRequest,
  MembershipRole,
  MembershipRosterEntry,
} from '../../types/admin.ts'

type RequestFilter = 'all' | MembershipRole | 'pending'

export default function StaffFacultyManager({ accessToken }: { accessToken: string }) {
  const [requestFilter, setRequestFilter] = useState<RequestFilter>('pending')
  const [requests, setRequests] = useState<MembershipRequest[]>([])
  const [members, setMembers] = useState<MembershipRosterEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [actionKey, setActionKey] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const role = requestFilter === 'staff' || requestFilter === 'faculty' ? requestFilter : undefined
      const status = requestFilter === 'pending' ? 'pending' : undefined
      const [requestData, rosterData] = await Promise.all([
        listMembershipRequests(accessToken, role, status),
        listMembershipRoster(accessToken),
      ])
      setRequests(requestData.requests)
      setMembers(rosterData.members)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load Staff & Faculty management.')
    } finally {
      setLoading(false)
    }
  }, [accessToken, requestFilter])

  useEffect(() => { void load() }, [load])

  async function decide(request: MembershipRequest, decision: 'approve' | 'reject') {
    const verb = decision === 'approve' ? 'approve' : 'reject'
    if (!window.confirm(`${verb[0].toUpperCase()}${verb.slice(1)} ${request.full_name || request.email}?`)) return
    setActionKey(`${decision}:${request.request_id}`)
    setError(null)
    setSuccess(null)
    try {
      const result = await decideMembershipRequest(accessToken, request.request_id, decision)
      setSuccess(result.message)
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : `Could not ${verb} this request.`)
    } finally {
      setActionKey(null)
    }
  }

  async function lifecycle(member: MembershipRosterEntry, action: 'deactivate' | 'reactivate') {
    if (!member.user_id) return
    if (!window.confirm(`${action === 'deactivate' ? 'Deactivate' : 'Reactivate'} ${member.name || member.email}?`)) return
    setActionKey(`${action}:${member.user_id}`)
    setError(null)
    setSuccess(null)
    try {
      const result = await changeMembershipStatus(accessToken, member.user_id, action)
      setSuccess(result.message)
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : `Could not ${action} this member.`)
    } finally {
      setActionKey(null)
    }
  }

  const buttonClass = 'rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-medium hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50'

  return (
    <div className="space-y-8">
      {error ? <p role="alert" className="rounded-lg border border-red-700 bg-red-950/40 p-3 text-sm text-red-200">{error}</p> : null}
      {success ? <p role="status" className="rounded-lg border border-emerald-700 bg-emerald-950/40 p-3 text-sm text-emerald-200">{success}</p> : null}

      <section aria-labelledby="membership-requests-heading" className="rounded-2xl border border-slate-700 bg-slate-800 p-4">
        <h2 id="membership-requests-heading" className="text-lg font-semibold text-white">Requests</h2>
        <div className="mt-3 flex flex-wrap gap-2" role="tablist" aria-label="Request filters">
          {(['all', 'staff', 'faculty', 'pending'] as const).map((filter) => (
            <button key={filter} type="button" role="tab" aria-selected={requestFilter === filter} onClick={() => setRequestFilter(filter)} className={`${buttonClass} ${requestFilter === filter ? 'bg-emerald-600 text-white' : 'text-slate-200'}`}>
              {filter[0].toUpperCase() + filter.slice(1)}
            </button>
          ))}
        </div>
        {loading ? <p role="status" className="mt-4 text-sm text-slate-300">Loading membership requests…</p> : requests.length === 0 ? <p className="mt-4 text-sm text-slate-400">No membership requests match this filter.</p> : (
          <div className="mt-4 space-y-3">
            {requests.map((request) => (
              <article key={request.request_id} className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-700 p-3">
                <div className="mr-auto min-w-0">
                  <p className="font-medium text-white">{request.full_name || 'Unnamed applicant'}</p>
                  <p className="break-all text-sm text-slate-300">{request.email}</p>
                  <p className="text-xs capitalize text-slate-400">{request.requested_role} · {request.status}</p>
                </div>
                {request.status === 'pending' ? <>
                  <button type="button" disabled={actionKey !== null} onClick={() => void decide(request, 'approve')} className={`${buttonClass} text-emerald-200`}>{actionKey === `approve:${request.request_id}` ? 'Approving…' : 'Approve'}</button>
                  <button type="button" disabled={actionKey !== null} onClick={() => void decide(request, 'reject')} className={`${buttonClass} text-red-200`}>{actionKey === `reject:${request.request_id}` ? 'Rejecting…' : 'Reject'}</button>
                </> : null}
              </article>
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="membership-roster-heading" className="rounded-2xl border border-slate-700 bg-slate-800 p-4">
        <h2 id="membership-roster-heading" className="text-lg font-semibold text-white">Roster</h2>
        {loading ? <p role="status" className="mt-4 text-sm text-slate-300">Loading roster…</p> : members.length === 0 ? <p className="mt-4 text-sm text-slate-400">No staff or faculty are on the roster yet.</p> : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead className="text-xs uppercase text-slate-400"><tr><th className="p-2">Name</th><th className="p-2">Email</th><th className="p-2">Role</th><th className="p-2">Status</th><th className="p-2">Actions</th></tr></thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.user_id} className="border-t border-slate-700">
                    <td className="p-2 text-white">{member.name || 'Pending setup'}</td>
                    <td className="p-2 text-slate-300">{member.email}</td>
                    <td className="p-2 capitalize text-slate-300">{member.role}</td>
                    <td className="p-2 capitalize text-slate-300">{member.status}</td>
                    <td className="p-2">
                      {member.user_id && member.status === 'active' ? <button type="button" disabled={actionKey !== null} onClick={() => void lifecycle(member, 'deactivate')} className={buttonClass}>{actionKey === `deactivate:${member.user_id}` ? 'Deactivating…' : 'Deactivate'}</button> : null}
                      {member.user_id && (member.status === 'inactive' || member.status === 'deactivated') ? <button type="button" disabled={actionKey !== null} onClick={() => void lifecycle(member, 'reactivate')} className={buttonClass}>{actionKey === `reactivate:${member.user_id}` ? 'Reactivating…' : 'Reactivate'}</button> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
