import type { InstitutionSummary } from '../../../types/platform.ts'

/** The canonical institution lifecycle, reusing the Phase 6.13 status values. */
export function StatusPill({ status }: { status: string }) {
  const label =
    status === 'active'
      ? 'Active'
      : status === 'suspended'
        ? 'Suspended'
        : status === 'pending'
          ? 'Pending'
          : 'Rejected'
  const tone =
    status === 'active'
      ? 'border-success bg-success-bg text-success'
      : status === 'suspended'
        ? 'border-warning bg-warning-bg text-warning'
        : 'border-control bg-raised text-muted'
  return <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${tone}`}>{label}</span>
}

export const inputClass =
  'w-full rounded-lg border border-control bg-surface px-3 py-2 text-sm text-content placeholder-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent'

export const labelClass = 'mb-1 block text-xs font-semibold uppercase tracking-wide text-muted'

export function InstitutionTable({
  institutions,
  loading,
  onOpen,
}: {
  institutions: InstitutionSummary[]
  loading: boolean
  onOpen: (id: string) => void
}) {
  if (loading) {
    return (
      <p role="status" className="text-sm text-muted">
        Loading institutions...
      </p>
    )
  }
  if (institutions.length === 0) {
    return (
      <p className="rounded-xl border border-line bg-surface px-5 py-8 text-center text-sm text-muted">
        No institutions have been created yet. Use "Create Institution" to add the first one.
      </p>
    )
  }
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-surface">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Institutions registered on the platform</caption>
        <thead className="border-b border-line bg-surface text-xs uppercase tracking-wide text-muted">
          <tr>
            <th scope="col" className="px-5 py-3 font-semibold">
              Institution
            </th>
            <th scope="col" className="px-5 py-3 font-semibold">
              Code
            </th>
            <th scope="col" className="px-5 py-3 font-semibold">
              Status
            </th>
            <th scope="col" className="px-5 py-3 font-semibold">
              Admins
            </th>
            <th scope="col" className="px-5 py-3 font-semibold">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {institutions.map((institution) => (
            <tr key={institution.id} className="hover:bg-hover">
              <td className="px-5 py-4 font-medium text-content">{institution.name}</td>
              <td className="px-5 py-4 font-mono text-xs text-muted">{institution.code}</td>
              <td className="px-5 py-4">
                <StatusPill status={institution.status} />
              </td>
              <td className="px-5 py-4 text-muted">{institution.admin_count}</td>
              <td className="px-5 py-4 text-right">
                <button
                  type="button"
                  onClick={() => {
                    onOpen(institution.id)
                  }}
                  className="rounded-lg border border-control px-3 py-2 text-xs font-medium text-content hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
                >
                  Manage
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
