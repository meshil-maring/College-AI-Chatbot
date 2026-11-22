import { useState } from 'react'
import { Badge, BUTTON_CLASS, DANGER_BUTTON_CLASS, Feedback } from '../StaffFacultyUI.tsx'
import AdminAccessEditor from './AdminAccessEditor.tsx'
import AdminProfileEditor from './AdminProfileEditor.tsx'
import { profileSummary } from './adminProfile.ts'
import { accessSummary } from './accessAreas.ts'
import InviteAdminForm from './InviteAdminForm.tsx'
import { useInstitutionAdmins } from './useInstitutionAdmins.ts'

/**
 * Institution administrators. The Owner always has full access and alone
 * invites, limits or removes administrators and can hand ownership to another.
 * The Owner edits anyone's employee profile; an administrator edits their own.
 */
export default function AdministratorsPage({ accessToken }: { accessToken: string }) {
  const model = useInstitutionAdmins(accessToken)
  const busy = model.actionKey !== null
  // One open editor at a time: which administrator, and access or profile.
  const [editing, setEditing] = useState<string | null>(null)
  const toggle = (key: string) => setEditing(editing === key ? null : key)

  return (
    <div className="space-y-4">
      <Feedback error={model.error} success={model.notice} onDismiss={model.dismiss} />
      {!model.loading && !model.viewerIsOwner ? (
        <p className="rounded-lg border border-line bg-surface p-3 text-sm text-muted">
          Only the institution Owner can invite or remove administrators.
        </p>
      ) : null}
      {model.viewerIsOwner ? <InviteAdminForm model={model} /> : null}

      <section
        aria-labelledby="administrators-heading"
        className="space-y-3 rounded-xl border border-line bg-surface p-4"
      >
        <h3 id="administrators-heading" className="text-sm font-semibold text-content">
          Administrators
        </h3>
        {model.loading ? <p className="text-sm text-muted">Loading…</p> : null}
        {model.loadError ? (
          <p role="alert" className="text-sm text-danger">
            {model.loadError}
          </p>
        ) : null}
        <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line">
          {model.administrators.map((admin) => (
            <li key={admin.user_id} className="flex flex-wrap items-center gap-3 px-3 py-3">
              <div className="mr-auto flex min-w-0 flex-col">
                <span className="flex flex-wrap items-center gap-2 text-sm font-medium text-content">
                  {admin.name}
                  {admin.is_owner ? <Badge tone="accent">Owner</Badge> : null}
                  {admin.status === 'active' ? null : <Badge tone="warning">{admin.status}</Badge>}
                </span>
                <span className="break-all text-sm text-muted">{admin.email}</span>
                <span className="flex flex-wrap items-center gap-2 text-xs text-muted">
                  {profileSummary(admin.profile) ?? <Badge tone="warning">Profile incomplete</Badge>}
                  <span>{admin.is_owner ? 'Full access (Owner)' : accessSummary(admin.access_areas)}</span>
                </span>
              </div>
              {model.viewerIsOwner || admin.user_id === model.viewerId ? (
                <button
                  type="button"
                  disabled={busy}
                  aria-expanded={editing === `profile:${admin.user_id}`}
                  aria-label={`Edit profile of ${admin.name}`}
                  onClick={() => toggle(`profile:${admin.user_id}`)}
                  className={BUTTON_CLASS}
                >
                  Edit profile
                </button>
              ) : null}
              {model.viewerIsOwner && !admin.is_owner ? (
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy || admin.status !== 'active'}
                    aria-expanded={editing === `access:${admin.user_id}`}
                    aria-label={`Edit access for ${admin.name}`}
                    onClick={() => toggle(`access:${admin.user_id}`)}
                    className={BUTTON_CLASS}
                  >
                    Edit access
                  </button>
                  <button
                    type="button"
                    disabled={busy || admin.status !== 'active'}
                    aria-label={`Make ${admin.name} the Owner`}
                    onClick={() => void model.transfer(admin)}
                    className={BUTTON_CLASS}
                  >
                    Make Owner
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    aria-label={`Remove ${admin.name} as administrator`}
                    onClick={() => void model.revoke(admin)}
                    className={DANGER_BUTTON_CLASS}
                  >
                    {model.actionKey === `revoke:${admin.user_id}` ? 'Removing…' : 'Remove'}
                  </button>
                </div>
              ) : null}
              {editing === `access:${admin.user_id}` && model.viewerIsOwner && !admin.is_owner ? (
                <AdminAccessEditor admin={admin} model={model} onDone={() => setEditing(null)} />
              ) : null}
              {editing === `profile:${admin.user_id}` ? (
                <AdminProfileEditor admin={admin} model={model} onDone={() => setEditing(null)} />
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      {model.viewerIsOwner && model.invitations.length ? (
        <section
          aria-labelledby="admin-invitations-heading"
          className="space-y-3 rounded-xl border border-line bg-surface p-4"
        >
          <h3 id="admin-invitations-heading" className="text-sm font-semibold text-content">
            Pending administrator invitations
          </h3>
          <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line">
            {model.invitations.map((invitation) => (
              <li key={invitation.invitation_id} className="flex flex-wrap items-center gap-3 px-3 py-3">
                <span className="mr-auto flex min-w-0 flex-col text-sm">
                  <span className="font-medium text-content">{invitation.full_name || invitation.email}</span>
                  {invitation.full_name ? <span className="break-all text-muted">{invitation.email}</span> : null}
                  <span className="text-xs text-muted">{accessSummary(invitation.access_areas)}</span>
                </span>
                <button
                  type="button"
                  disabled={busy}
                  aria-label={`Resend the invitation to ${invitation.email}`}
                  onClick={() => void model.resend(invitation)}
                  className={BUTTON_CLASS}
                >
                  {model.actionKey === `resend:${invitation.invitation_id}` ? 'Sending…' : 'Resend'}
                </button>
                <button
                  type="button"
                  disabled={busy}
                  aria-label={`Cancel the invitation for ${invitation.email}`}
                  onClick={() => void model.cancel(invitation)}
                  className={BUTTON_CLASS}
                >
                  Cancel invitation
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  )
}
