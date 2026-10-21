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
      <div className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-slate-700 bg-slate-900 p-6">
        <div>
          <h2 className="text-2xl font-bold text-white">{institution.name}</h2>
          <p className="mt-1 font-mono text-sm text-slate-400">{institution.code}</p>
          <p className="mt-3 text-xs text-slate-500">
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
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-300 disabled:opacity-50"
            >
              {busy === 'activate' ? 'Approving...' : 'Approve & Activate'}
            </button>
          ) : institution.status === 'suspended' ? (
            <button
              type="button"
              onClick={onActivate}
              disabled={busy !== null}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-300 disabled:opacity-50"
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
              className="rounded-lg border border-amber-500/50 px-4 py-2 text-sm font-semibold text-amber-300 hover:bg-amber-500/10 focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:opacity-50"
            >
              Suspend Institution
            </button>
          )}
        </div>
      </div>

      {localError !== null ? (
        <p role="alert" className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {localError}
        </p>
      ) : null}

      {confirmApproval ? (
        <div
          role="alertdialog"
          aria-label="Confirm institution approval"
          className="rounded-2xl border border-emerald-500/50 bg-emerald-500/10 p-6"
        >
          <h3 className="text-lg font-semibold text-emerald-200">Approve {institution.name}?</h3>
          <p className="mt-2 text-sm leading-6 text-emerald-100/90">
            This activates the university and allows its assigned University Admins to use the protected institution
            workspace.
          </p>
          <div className="mt-5 flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setConfirmApproval(false)
              }}
              className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-300"
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
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-300 disabled:opacity-50"
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
          className="rounded-2xl border border-amber-500/50 bg-amber-500/10 p-6"
        >
          <h3 className="text-lg font-semibold text-amber-200">Suspend {institution.name}?</h3>
          <p className="mt-2 text-sm leading-6 text-amber-100/90">
            Existing data will be retained and no accounts are revoked. Institutional access will be restricted until
            the institution is activated again.
          </p>
          <div className="mt-5 flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setConfirmSuspend(false)
              }}
              className="rounded-lg border border-amber-500/50 px-4 py-2 text-sm font-medium text-amber-100 hover:bg-amber-500/10 focus:outline-none focus:ring-2 focus:ring-amber-300"
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
              className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:opacity-50"
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
            <dd className="text-sm text-slate-200">{institution.is_active ? 'Active' : 'Restricted'}</dd>
          </div>
          <div>
            <dt className={labelClass}>University admins</dt>
            <dd className="text-sm text-slate-200">{institution.admin_count}</dd>
          </div>
        </dl>
        <p className="mt-4 text-xs leading-5 text-slate-500">
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
