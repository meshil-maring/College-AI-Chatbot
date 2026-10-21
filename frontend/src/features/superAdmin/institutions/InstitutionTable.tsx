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
      ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
      : status === 'suspended'
        ? 'border-amber-500/40 bg-amber-500/10 text-amber-300'
        : 'border-slate-500/40 bg-slate-500/10 text-slate-300'
  return <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${tone}`}>{label}</span>
}

export const inputClass =
  'w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-violet-400 focus:outline-none focus:ring-1 focus:ring-violet-400'

export const labelClass = 'mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400'

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
      <p role="status" className="text-sm text-slate-400">
        Loading institutions...
      </p>
    )
  }
  if (institutions.length === 0) {
    return (
      <p className="rounded-xl border border-slate-700 bg-slate-900 px-5 py-8 text-center text-sm text-slate-400">
        No institutions have been created yet. Use "Create Institution" to add the first one.
      </p>
    )
  }
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-700 bg-slate-900">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Institutions registered on the platform</caption>
        <thead className="border-b border-slate-700 bg-slate-800/60 text-xs uppercase tracking-wide text-slate-400">
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
            <tr key={institution.id} className="hover:bg-slate-800/40">
              <td className="px-5 py-4 font-medium text-white">{institution.name}</td>
              <td className="px-5 py-4 font-mono text-xs text-slate-400">{institution.code}</td>
              <td className="px-5 py-4">
                <StatusPill status={institution.status} />
              </td>
              <td className="px-5 py-4 text-slate-300">{institution.admin_count}</td>
              <td className="px-5 py-4 text-right">
                <button
                  type="button"
                  onClick={() => {
                    onOpen(institution.id)
                  }}
                  className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-violet-300"
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
