import AdminRosterPanel from './AdminRosterPanel.tsx'
import { InstitutionAccountAssignment } from './institutions/InstitutionAccountAssignment.tsx'
import { InstitutionBasicInformation } from './institutions/InstitutionBasicInformation.tsx'
import { InstitutionBranding } from './institutions/InstitutionBranding.tsx'
import { StatusPill } from './institutions/InstitutionTable.tsx'

/**
 * Institution detail view: basic information, lifecycle, branding, admin
 * assignment and clearly-labelled future areas.
 *
 * Status is intentionally NOT editable here — it is changed only through the
 * dedicated Suspend/Activate actions, mirroring the backend contract where a
 * generic PATCH cannot carry a status field.
 */

import { labelClass, Section } from './institutions/InstitutionSection.tsx'
import { useInstitutionDetail } from './institutions/useInstitutionDetail.ts'
export type { BusyAction } from './institutions/useInstitutionDetail.ts'

export default function InstitutionDetailPanel(props: Parameters<typeof useInstitutionDetail>[0]) {
  const model = useInstitutionDetail(props)
  const {
    institution,
    busy,
    onSuspend,
    onActivate,
    onRosterChanged,
    localError,
    confirmSuspend,
    setConfirmSuspend,
    confirmApproval,
    setConfirmApproval,
  } = model

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4 rounded-xl border border-line bg-surface p-6">
        <div>
          <h2 className="font-bold text-content text-section">{institution.name}</h2>
          <p className="mt-1 font-mono text-sm text-muted">{institution.code}</p>
          <p className="mt-3 text-xs text-muted">
            Public AI entry: <span className="font-mono">/u/{institution.code.toLowerCase()}/ai</span>
          </p>
        </div>
        <div className="flex flex-col items-end gap-3">
          <StatusPill status={institution.status} />
          {institution.status === 'pending' ? (
            <button
              type="button"
              onClick={() => {
                setConfirmApproval(true)
              }}
              disabled={busy !== null}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
            >
              {busy === 'activate' ? 'Approving...' : 'Approve & Activate'}
            </button>
          ) : institution.status === 'suspended' ? (
            <button
              type="button"
              onClick={onActivate}
              disabled={busy !== null}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
            >
              {busy === 'activate' ? 'Activating...' : 'Activate Institution'}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => {
                setConfirmSuspend(true)
              }}
              disabled={busy !== null}
              className="rounded-lg border border-warning px-4 py-2 text-sm font-semibold text-warning hover:bg-warning-bg focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
            >
              Suspend Institution
            </button>
          )}
        </div>
      </div>

      {localError !== null ? (
        <p role="alert" className="rounded-xl border border-danger bg-danger-bg px-4 py-3 text-sm text-danger">
          {localError}
        </p>
      ) : null}

      {confirmApproval ? (
        <div
          role="alertdialog"
          aria-label="Confirm institution approval"
          className="rounded-xl border border-success bg-success-bg p-6"
        >
          <h3 className="font-semibold text-success text-card">Approve {institution.name}?</h3>
          <p className="mt-2 text-sm leading-6 text-success">
            This activates the university and allows its assigned University Admins to use the protected institution
            workspace.
          </p>
          <div className="mt-5 flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setConfirmApproval(false)
              }}
              className="rounded-lg border border-control px-4 py-2 text-sm font-medium text-content hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => {
                setConfirmApproval(false)
                onActivate()
              }}
              disabled={busy !== null}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
            >
              {busy === 'activate' ? 'Approving...' : 'Approve & Activate'}
            </button>
          </div>
        </div>
      ) : null}

      {confirmSuspend ? (
        <div
          role="alertdialog"
          aria-label="Confirm suspension"
          className="rounded-xl border border-warning bg-warning-bg p-6"
        >
          <h3 className="font-semibold text-warning text-card">Suspend {institution.name}?</h3>
          <p className="mt-2 text-sm leading-6 text-warning">
            Existing data will be retained and no accounts are revoked. Institutional access will be restricted until
            the institution is activated again.
          </p>
          <div className="mt-5 flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setConfirmSuspend(false)
              }}
              className="rounded-lg border border-warning px-4 py-2 text-sm font-medium text-warning hover:bg-warning-bg focus:outline-none focus:ring-2 focus:ring-accent"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => {
                setConfirmSuspend(false)
                onSuspend()
              }}
              disabled={busy !== null}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
            >
              {busy === 'suspend' ? 'Suspending...' : 'Suspend Institution'}
            </button>
          </div>
        </div>
      ) : null}

      <InstitutionBasicInformation model={model} />

      <Section title="Status">
        <dl className="grid gap-4 sm:grid-cols-3">
          <div>
            <dt className={labelClass}>Lifecycle status</dt>
            <dd>
              <StatusPill status={institution.status} />
            </dd>
          </div>
          <div>
            <dt className={labelClass}>Availability</dt>
            <dd className="text-sm text-content">{institution.is_active ? 'Active' : 'Restricted'}</dd>
          </div>
          <div>
            <dt className={labelClass}>University admins</dt>
            <dd className="text-sm text-content">{institution.admin_count}</dd>
          </div>
        </dl>
        <p className="mt-4 text-xs leading-5 text-muted">
          Status changes only through the Approve / Suspend / Activate actions above, and each change is recorded in the
          platform audit ledger.
        </p>
      </Section>

      <InstitutionBranding model={model} />

      <AdminRosterPanel institutionId={institution.id} institutionCode={institution.code} onChanged={onRosterChanged} />

      <InstitutionAccountAssignment model={model} />

      <Section title="Public AI" comingSoon />
      <Section title="Public Knowledge" comingSoon />
      <Section title="Platform Information" comingSoon />
    </div>
  )
}
