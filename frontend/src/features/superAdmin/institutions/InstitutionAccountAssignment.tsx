import { inputClass, labelClass, Section } from './InstitutionSection.tsx'
import type { InstitutionDetailPanelModel } from './useInstitutionDetail.ts'
export function InstitutionAccountAssignment({ model }: { model: InstitutionDetailPanelModel }) {
  const { institution, busy, onAssign, showAssign, setShowAssign, adminEmail, setAdminEmail } = model
  return (
    <Section title="Assign Existing Account" comingSoon={false}>
      <p className="text-sm leading-6 text-muted">
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
          className="rounded-lg border border-control px-4 py-2 text-sm font-medium text-content hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
        >
          Assign University Admin
        </button>
        <span className="text-sm text-muted">{institution.admin_count} assigned</span>
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
            className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
          >
            {busy === 'assign' ? 'Assigning...' : 'Assign'}
          </button>
        </form>
      ) : null}
    </Section>
  )
}
