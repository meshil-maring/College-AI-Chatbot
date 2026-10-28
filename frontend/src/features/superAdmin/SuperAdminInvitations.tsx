import { useState } from 'react'
import { useApiMutation, useApiQuery } from '../../hooks/useApiQuery.ts'
import {
  SuperAdminInvitationError,
  cancelSuperAdminInvitation,
  createSuperAdminInvitation,
  listSuperAdminInvitations,
  type SuperAdminInvitation,
} from '../../services/invitations/superAdminInvitationApi.ts'
import { useAuth } from '../auth/session/AuthProvider.tsx'
import { hasPermission } from '../auth/access/permissions.ts'

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
    try {
      await invitationsQuery.refetch()
    } catch (err) {
      setError(message(err))
    }
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
      <h2 id="sa-invites-title" className="font-bold text-content text-section">
        Super Admins
      </h2>
      {canManage ? (
        <form
          onSubmit={(e) => {
            void invite(e)
          }}
          className="flex gap-3"
        >
          <input
            type="email"
            aria-label="Invitee email"
            value={email}
            maxLength={320}
            onChange={(e) => {
              setEmail(e.target.value)
            }}
            placeholder="new.admin@example.com"
            className="flex-1 rounded-lg border border-control bg-surface px-3 py-2 text-sm text-content"
          />
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink disabled:opacity-60"
          >
            Invite Super Admin
          </button>
        </form>
      ) : null}
      {error !== null ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      {link !== null ? (
        <p role="status" className="break-all rounded-lg border border-success bg-success-bg p-3 text-sm text-success">
          Share this single-use link (shown once, valid 24 hours): {link}
        </p>
      ) : null}
      <ul className="divide-y divide-slate-800 rounded-lg border border-line">
        {invitations.length === 0 ? <li className="p-3 text-sm text-muted">No invitations yet.</li> : null}
        {invitations.map((item) => (
          <li key={item.invitation_id} className="flex items-center justify-between gap-3 p-3 text-sm">
            <span>
              {item.email} · <span className="text-muted">{item.status}</span>
            </span>
            {canManage && item.status === 'invited' ? (
              <button
                type="button"
                onClick={() => {
                  void cancel(item.invitation_id)
                }}
                className="text-xs text-warning underline"
              >
                Cancel
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  )
}
