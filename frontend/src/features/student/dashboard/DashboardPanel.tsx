/** Shared building blocks for the student dashboard panels. */

import type { ReactNode } from 'react'
import { ArrowRight, Hourglass, type LucideIcon } from 'lucide-react'
import { ErrorBlock, LoadingBlock } from '../shared/SectionState.tsx'
import type { DashboardRead } from './useDashboardData.ts'

export function DashboardPanel({
  icon: Icon,
  title,
  headingId,
  action,
  children,
}: {
  icon: LucideIcon
  title: string
  headingId: string
  action?: ReactNode
  children: ReactNode
}) {
  return (
    <section aria-labelledby={headingId} className="min-w-0 rounded-xl border border-line bg-surface p-4 sm:p-5">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
        <h2 id={headingId} className="flex min-w-0 items-center gap-2 text-card font-semibold text-content">
          <Icon aria-hidden="true" className="h-5 w-5 shrink-0 text-accent" />
          <span className="min-w-0 break-words">{title}</span>
        </h2>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      <div className="mt-3">{children}</div>
    </section>
  )
}

/**
 * Link-styled button that opens the full page behind a panel. Without
 * `onClick` the page does not exist yet: it renders muted and disabled,
 * with a "Coming soon" hint, so panel headers still line up.
 */
export function ViewAllButton({ label = 'View all', onClick }: { label?: string; onClick?: () => void }) {
  if (!onClick)
    return (
      <button
        type="button"
        disabled
        title="Coming soon"
        className="inline-flex cursor-not-allowed items-center gap-1 text-sm font-medium text-muted opacity-70"
      >
        {label}
        <ArrowRight aria-hidden="true" className="h-4 w-4" />
      </button>
    )
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1 rounded-sm text-sm font-medium text-accent underline-offset-4 hover:underline focus:outline-none focus:ring-2 focus:ring-accent"
    >
      {label}
      <ArrowRight aria-hidden="true" className="h-4 w-4" />
    </button>
  )
}

/** Small pill marking a feature whose backend API does not exist yet. */
export function ComingSoonBadge() {
  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-warning bg-warning-bg px-2 py-0.5 text-xs font-medium text-warning">
      <Hourglass aria-hidden="true" className="h-3 w-3" />
      Coming soon
    </span>
  )
}

/** Panel body for a feature that is not available yet. */
export function ComingSoon({ message }: { message: string }) {
  return (
    <div role="status" className="flex flex-col items-start gap-2 py-4">
      <ComingSoonBadge />
      <p className="text-sm text-muted">{message}</p>
    </div>
  )
}

/** Shared loading / error / unavailable handling for one dashboard read. */
export function ReadState<T>({
  read,
  loadingLabel,
  errorMessage,
  unavailableMessage,
  children,
}: {
  read: DashboardRead<T>
  loadingLabel: string
  errorMessage: string
  unavailableMessage: string
  children: (data: T | null) => ReactNode
}) {
  if (read.status === 'unavailable') return <p className="text-sm text-muted">{unavailableMessage}</p>
  if (read.status === 'loading') return <LoadingBlock label={loadingLabel} />
  if (read.status === 'error') return <ErrorBlock message={errorMessage} onRetry={read.retry} />
  return <>{children(read.data)}</>
}
