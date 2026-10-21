export const inputClass =
  'w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-violet-400 focus:outline-none focus:ring-1 focus:ring-violet-400'

export const labelClass = 'mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400'

export function Section({
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
