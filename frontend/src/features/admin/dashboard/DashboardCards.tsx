import { type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

/** One metric tile. `value === null` renders as "Unavailable", never as 0. */
export function MetricTile({
  label,
  value,
  icon: Icon,
  tone = 'default',
}: {
  label: string
  value: number | null
  icon: LucideIcon
  tone?: 'default' | 'accent'
}) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800 p-4">
      <div className="flex items-start justify-between gap-3">
        <div
          className={tone === 'accent' ? 'text-2xl font-bold text-amber-400' : 'text-2xl font-bold text-emerald-400'}
        >
          {value === null ? '—' : value}
        </div>
        <Icon
          aria-hidden="true"
          className={tone === 'accent' ? 'h-5 w-5 text-amber-400' : 'h-5 w-5 text-emerald-400'}
        />
      </div>
      <div className="mt-1 text-xs text-slate-400">{label}</div>
      {value === null ? <div className="mt-1 text-[11px] text-slate-500">Unavailable</div> : null}
    </div>
  )
}

export function SectionCard({ title, icon: Icon, children }: { title: string; icon: LucideIcon; children: ReactNode }) {
  return (
    <section className="min-w-0 rounded-2xl border border-slate-700 bg-slate-800/50 p-5">
      <h3 className="flex items-center gap-2 break-words text-sm font-semibold uppercase tracking-wide text-slate-300">
        <Icon aria-hidden="true" className="h-4 w-4 shrink-0 text-emerald-400" />
        {title}
      </h3>
      <div className="mt-4">{children}</div>
    </section>
  )
}
