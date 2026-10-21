import { inputClass, labelClass, Section } from './InstitutionSection.tsx'
import type { InstitutionDetailPanelModel } from './useInstitutionDetail.ts'
export function InstitutionAccountAssignment({ model }: { model: InstitutionDetailPanelModel }) {
  const { institution, busy, onAssign, showAssign, setShowAssign, adminEmail, setAdminEmail } = model
  return (
    <Section title="Assign Existing Account" comingSoon={false}>
      <p className="text-sm leading-6 text-slate-400">
        Phase 7.13 capability, preserved unchanged: grant the institution-scoped admin role to an account that ALREADY
        exists. This does not create an account and does not accept a password; the granted role is always the
        institution-scoped admin role. Prefer &quot;+ Invite Admin&quot; above for a new University Admin.
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => {
            setShowAssign((open) => !open)
          }}
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
            <label className={labelClass} htmlFor="assign-email">
              Existing account email
            </label>
            <input
              id="assign-email"
              type="email"
              className={inputClass}
              value={adminEmail}
              onChange={(event) => {
                setAdminEmail(event.target.value)
              }}
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
  )
}
