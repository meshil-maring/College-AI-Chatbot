import { Badge, BUTTON_CLASS, DANGER_BUTTON_CLASS, Feedback } from '../StaffFacultyUI.tsx'
import InviteAdminForm from './InviteAdminForm.tsx'
import { useInstitutionAdmins } from './useInstitutionAdmins.ts'

/**
 * Institution administrators. Every administrator has full access; the Owner
 * alone invites or removes administrators and can hand ownership to another.
 */
export default function AdministratorsPage({ accessToken }: { accessToken: string }) {
  const model = useInstitutionAdmins(accessToken)
  const busy = model.actionKey !== null

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
              </div>
              {model.viewerIsOwner && !admin.is_owner ? (
                <div className="flex flex-wrap gap-2">
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
                </span>
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
