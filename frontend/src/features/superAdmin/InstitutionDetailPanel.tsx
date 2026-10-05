import { useState } from 'react'
import { updateInstitution } from '../../services/platformInstitutionsApi.ts'
import type { InstitutionDetail } from '../../types/platform.ts'
import { useAuth } from '../auth/AuthProvider.tsx'
import { StatusPill } from './InstitutionManagement.tsx'
import AdminRosterPanel from './AdminRosterPanel.tsx'

/** Which mutation is in flight, so the UI can disable conflicting actions. */
export type BusyAction = 'create' | 'save' | 'suspend' | 'activate' | 'assign' | null

const inputClass =
  'w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-violet-400 focus:outline-none focus:ring-1 focus:ring-violet-400'
const labelClass = 'mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400'

function Section({
  title,
  children,
  comingSoon = false,
}: {
  title: string
  children?: React.ReactNode
  comingSoon?: boolean
}) {
  return (
    <section className="rounded-2xl border border-slate-700 bg-slate-900 p-6">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold text-white">{title}</h3>
        {comingSoon ? (
          <span className="rounded-full bg-slate-500/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
            Coming Soon
          </span>
        ) : null}
      </div>
      {comingSoon ? (
        <p className="mt-3 text-sm leading-6 text-slate-500">
          Not implemented in Phase 7.13. No placeholder behaviour is simulated.
        </p>
      ) : (
        <div className="mt-4">{children}</div>
      )}
    </section>
  )
}

/**
 * Institution detail view: basic information, lifecycle, branding, admin
 * assignment and clearly-labelled future areas.
 *
 * Status is intentionally NOT editable here — it is changed only through the
 * dedicated Suspend/Activate actions, mirroring the backend contract where a
 * generic PATCH cannot carry a status field.
 */
export default function InstitutionDetailPanel({
  institution,
  busy,
  onSaved,
  onSuspend,
  onActivate,
  onAssign,
  onRosterChanged,
}: {
  institution: InstitutionDetail
  busy: BusyAction
  onSaved: (detail: InstitutionDetail) => void
  onSuspend: () => void
  onActivate: () => void
  onAssign: (email: string) => void
  /** Refresh the parent so `admin_count` reflects a roster change. */
  onRosterChanged?: () => void
}) {
  const { accessToken } = useAuth()
  const [name, setName] = useState(institution.name)
  const [code, setCode] = useState(institution.code)
  const [displayName, setDisplayName] = useState(institution.display_name ?? '')
  const [welcomeMessage, setWelcomeMessage] = useState(institution.welcome_message ?? '')
  const [primaryColor, setPrimaryColor] = useState(institution.primary_color ?? '')
  const [localError, setLocalError] = useState<string | null>(null)
  const [confirmSuspend, setConfirmSuspend] = useState(false)
  const [confirmApproval, setConfirmApproval] = useState(false)
  const [showAssign, setShowAssign] = useState(false)
  const [adminEmail, setAdminEmail] = useState('')

  const [saving, setSaving] = useState(false)

  /**
   * Persist the edited configuration through the same authenticated client the
   * rest of this screen uses, sending ONLY the fields that actually changed so
   * a partial update can never blank an untouched value.
   */
  const saveConfiguration = async (): Promise<void> => {
    setLocalError(null)
    const input: Record<string, string> = {}
    if (name.trim() !== '' && name.trim() !== institution.name) input.name = name.trim()
    if (code.trim() !== '' && code.trim() !== institution.code) input.code = code.trim()
    if (displayName.trim() !== (institution.display_name ?? '')) {
      input.display_name = displayName.trim()
    }
    if (welcomeMessage.trim() !== (institution.welcome_message ?? '')) {
      input.welcome_message = welcomeMessage.trim()
    }
    if (primaryColor.trim() !== (institution.primary_color ?? '')) {
      input.primary_color = primaryColor.trim()
    }
    if (Object.keys(input).length === 0) return
    setSaving(true)
    try {
      onSaved(await updateInstitution(accessToken ?? '', institution.id, input))
    } catch (error) {
      setLocalError(
        error instanceof Error ? error.message : 'Could not save the configuration. Please try again.',
      )
    } finally {
      setSaving(false)
    }
  }

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
              onClick={() => { setConfirmApproval(true) }}
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
              onClick={() => { setConfirmSuspend(true) }}
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
        <div role="alertdialog" aria-label="Confirm institution approval" className="rounded-2xl border border-emerald-500/50 bg-emerald-500/10 p-6">
          <h3 className="text-lg font-semibold text-emerald-200">Approve {institution.name}?</h3>
          <p className="mt-2 text-sm leading-6 text-emerald-100/90">
            This activates the university and allows its assigned University Admins to use the protected institution workspace.
          </p>
          <div className="mt-5 flex items-center gap-3">
            <button
              type="button"
              onClick={() => { setConfirmApproval(false) }}
              className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-300"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => { setConfirmApproval(false); onActivate() }}
              disabled={busy !== null}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-300 disabled:opacity-50"
            >
              {busy === 'activate' ? 'Approving...' : 'Approve & Activate'}
            </button>
          </div>
        </div>
      ) : null}

      {confirmSuspend ? (
        <div role="alertdialog" aria-label="Confirm suspension" className="rounded-2xl border border-amber-500/50 bg-amber-500/10 p-6">
          <h3 className="text-lg font-semibold text-amber-200">Suspend {institution.name}?</h3>
          <p className="mt-2 text-sm leading-6 text-amber-100/90">
            Existing data will be retained and no accounts are revoked. Institutional access will be
            restricted until the institution is activated again.
          </p>
          <div className="mt-5 flex items-center gap-3">
            <button
              type="button"
              onClick={() => { setConfirmSuspend(false) }}
              className="rounded-lg border border-amber-500/50 px-4 py-2 text-sm font-medium text-amber-100 hover:bg-amber-500/10 focus:outline-none focus:ring-2 focus:ring-amber-300"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => { setConfirmSuspend(false); onSuspend() }}
              disabled={busy !== null}
              className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:opacity-50"
            >
              {busy === 'suspend' ? 'Suspending...' : 'Suspend Institution'}
            </button>
          </div>
        </div>
      ) : null}

      <Section title="Basic Information">
        <div className="grid gap-5 lg:grid-cols-2">
          <div>
            <label className={labelClass} htmlFor="detail-name">Institution name</label>
            <input
              id="detail-name"
              className={inputClass}
              value={name}
              onChange={(event) => { setName(event.target.value) }}
            />
          </div>
          <div>
            <label className={labelClass} htmlFor="detail-code">Institution code</label>
            <input
              id="detail-code"
              className={inputClass}
              value={code}
              onChange={(event) => { setCode(event.target.value) }}
            />
            <p className="mt-1 text-xs text-slate-500">
              Changing this changes the public URL. Existing codes are never rewritten silently.
            </p>
          </div>
        </div>
        <div className="mt-5">
          <button
            type="button"
            onClick={() => { void saveConfiguration() }}
            disabled={saving}
            className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-300 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save changes'}
          </button>
        </div>
      </Section>

      <Section title="Status">
        <dl className="grid gap-4 sm:grid-cols-3">
          <div>
            <dt className={labelClass}>Lifecycle status</dt>
            <dd><StatusPill status={institution.status} /></dd>
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
          Status changes only through the Approve / Suspend / Activate actions above, and each change is
          recorded in the platform audit ledger.
        </p>
      </Section>

      <Section title="Branding">
        <div className="grid gap-5 lg:grid-cols-2">
          <div>
            <label className={labelClass} htmlFor="detail-display">Display name</label>
            <input
              id="detail-display"
              className={inputClass}
              value={displayName}
              onChange={(event) => { setDisplayName(event.target.value) }}
              placeholder="Falls back to the institution name"
            />
          </div>
          <div>
            <label className={labelClass} htmlFor="detail-color">Primary colour</label>
            <input
              id="detail-color"
              className={inputClass}
              value={primaryColor}
              onChange={(event) => { setPrimaryColor(event.target.value) }}
              placeholder="#0F172A"
            />
          </div>
          <div className="lg:col-span-2">
            <label className={labelClass} htmlFor="detail-welcome">Welcome message</label>
            <input
              id="detail-welcome"
              className={inputClass}
              value={welcomeMessage}
              onChange={(event) => { setWelcomeMessage(event.target.value) }}
              placeholder="Shown on the public institution gateway"
            />
          </div>
        </div>
      </Section>

      <AdminRosterPanel
        institutionId={institution.id}
        institutionCode={institution.code}
        onChanged={onRosterChanged}
      />

      <Section title="Assign Existing Account" comingSoon={false}>
        <p className="text-sm leading-6 text-slate-400">
          Phase 7.13 capability, preserved unchanged: grant the institution-scoped admin role to
          an account that ALREADY exists. This does not create an account and does not accept a
          password; the granted role is always the institution-scoped admin role. Prefer
          &quot;+ Invite Admin&quot; above for a new University Admin.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => { setShowAssign((open) => !open) }}
            className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-violet-300"
          >
            Assign University Admin
          </button>
          <span className="text-sm text-slate-400">{institution.admin_count} assigned</span>
        </div>
        {showAssign ? (
          <form
            className="mt-4 flex flex-wrap items-end gap-3"
            onSubmit={(event) => {
              event.preventDefault()
              if (adminEmail.trim() === '') return
              onAssign(adminEmail.trim())
              setAdminEmail('')
            }}
          >
            <div className="min-w-64 flex-1">
              <label className={labelClass} htmlFor="assign-email">Existing account email</label>
              <input
                id="assign-email"
                type="email"
                className={inputClass}
                value={adminEmail}
                onChange={(event) => { setAdminEmail(event.target.value) }}
                placeholder="dean@university.example"
                required
              />
            </div>
            <button
              type="submit"
              disabled={busy !== null || adminEmail.trim() === ''}
              className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-300 disabled:opacity-50"
            >
              {busy === 'assign' ? 'Assigning...' : 'Assign'}
            </button>
          </form>
        ) : null}
      </Section>

      <Section title="Public AI" comingSoon />
      <Section title="Public Knowledge" comingSoon />
      <Section title="Platform Information" comingSoon />
    </div>
  )
}
