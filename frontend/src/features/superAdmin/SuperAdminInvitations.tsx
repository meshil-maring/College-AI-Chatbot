import { useState } from 'react'
import { useApiMutation, useApiQuery } from '../../hooks/useApiQuery.ts'
import {
  SuperAdminInvitationError,
  cancelSuperAdminInvitation,
  createSuperAdminInvitation,
  listSuperAdminInvitations,
  type SuperAdminInvitation,
} from '../../services/superAdminInvitationApi.ts'
import { useAuth } from '../auth/AuthProvider.tsx'
import { hasPermission } from '../auth/permissions.ts'

/** Invite additional Super Admins. The server enforces authorization. */
export default function SuperAdminInvitations() {
  const { accessToken, user } = useAuth()
  const canManage = hasPermission(user?.effective_permissions, 'platform.manage')
  const [email, setEmail] = useState('')
  const [link, setLink] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const invitationsQuery = useApiQuery<SuperAdminInvitation[]>(
    ['platform', 'super-admin-invitations', accessToken],
    () => listSuperAdminInvitations(accessToken as string),
    accessToken !== null,
  )
  const inviteMutation = useApiMutation<{ invitation_url: string }, string>({
    mutationFn: (address) => createSuperAdminInvitation(accessToken as string, address),
  })
  const cancelMutation = useApiMutation<SuperAdminInvitation, string>({
    mutationFn: (id) => cancelSuperAdminInvitation(accessToken as string, id),
  })
  const invitations = invitationsQuery.data ?? []
  const busy = inviteMutation.isPending

  const message = (err: unknown): string =>
    err instanceof SuperAdminInvitationError ? err.message : 'Something went wrong. Please try again.'

  const refresh = async (): Promise<void> => {
    try { await invitationsQuery.refetch() } catch (err) { setError(message(err)) }
  }

  const invite = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault()
    if (accessToken === null || email.trim() === '') return
    setError(null)
    setLink(null)
    try {
      const created = await inviteMutation.mutateAsync(email.trim())
      setLink(`${window.location.origin}${created.invitation_url}`)
      setEmail('')
      await refresh()
    } catch (err) {
      setError(message(err))
    }
  }

  const cancel = async (id: string): Promise<void> => {
    if (accessToken === null) return
    try {
      await cancelMutation.mutateAsync(id)
      await refresh()
    } catch (err) {
      setError(message(err))
    }
  }

  return (
    <section aria-labelledby="sa-invites-title" className="space-y-6">
      <h2 id="sa-invites-title" className="text-xl font-bold text-white">Super Admins</h2>
      {canManage ? (
        <form onSubmit={(e) => { void invite(e) }} className="flex gap-3">
          <input
            type="email"
            aria-label="Invitee email"
            value={email}
            maxLength={320}
            onChange={(e) => { setEmail(e.target.value) }}
            placeholder="new.admin@example.com"
            className="flex-1 rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100"
          />
          <button type="submit" disabled={busy} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">
            Invite Super Admin
          </button>
        </form>
      ) : null}
      {error !== null ? <p role="alert" className="text-sm text-red-400">{error}</p> : null}
      {link !== null ? (
        <p role="status" className="break-all rounded-lg border border-emerald-700 bg-emerald-500/10 p-3 text-sm text-emerald-200">
          Share this single-use link (shown once, valid 24 hours): {link}
        </p>
      ) : null}
      <ul className="divide-y divide-slate-800 rounded-lg border border-slate-800">
        {invitations.length === 0 ? <li className="p-3 text-sm text-slate-400">No invitations yet.</li> : null}
        {invitations.map((item) => (
          <li key={item.invitation_id} className="flex items-center justify-between gap-3 p-3 text-sm">
            <span>{item.email} · <span className="text-slate-400">{item.status}</span></span>
            {canManage && item.status === 'invited' ? (
              <button type="button" onClick={() => { void cancel(item.invitation_id) }} className="text-xs text-amber-300 underline">Cancel</button>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  )
}
