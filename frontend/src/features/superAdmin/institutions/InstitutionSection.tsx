export const inputClass =
  'w-full rounded-lg border border-control bg-surface px-3 py-2 text-sm text-content placeholder-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent'

export const labelClass = 'mb-1 block text-xs font-semibold uppercase tracking-wide text-muted'

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
    <section className="rounded-xl border border-line bg-surface p-6">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold text-content text-card">{title}</h3>
        {comingSoon ? (
          <span className="rounded-full bg-raised px-2 py-1 text-xs font-semibold uppercase tracking-wide text-muted">
            Coming Soon
          </span>
        ) : null}
      </div>
      {comingSoon ? (
        <p className="mt-3 text-sm leading-6 text-muted">
          Not implemented in Phase 7.13. No placeholder behaviour is simulated.
        </p>
      ) : (
        <div className="mt-4">{children}</div>
      )}
    </section>
  )
}
