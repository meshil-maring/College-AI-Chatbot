/**
 * Phase 6.16 — Shared loading / empty / error primitives for the student
 * experience.
 *
 * The four data states are always DISTINCT and never conflated:
 *
 *   loading — data is still in flight   → a "Loading…" status line
 *   error   — the request failed        → a generic message + optional retry
 *   empty   — the request succeeded and
 *             the institution/student
 *             simply has no records    → neutral wording, no failure language
 *   loaded  — records are rendered
 *
 * An empty section never claims a system failure, and a loading section never
 * renders "0", "No results", or "No notices" (the Phase 6.16 requirement).
 *
 * Accessibility: loading uses `role="status"` (polite announcement), errors use
 * `role="alert"`, and retry controls are real `<button>` elements with text
 * labels — no information is communicated by colour alone.
 */

import type { ReactNode } from 'react'

/** Neutral, non-alarming loading indicator for one dashboard section. */
export function LoadingBlock({ label }: { label: string }) {
  return (
    <p role="status" className="flex items-center gap-2 text-sm text-muted">
      <span
        aria-hidden="true"
        className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-control border-t-transparent"
      />
      <span>{label}</span>
    </p>
  )
}

/** Empty state: data genuinely does not exist yet (never a failure). */
export function EmptyBlock({ message }: { message: string }) {
  return <p className="text-sm text-muted">{message}</p>
}

/** Error state: user-safe message plus an optional retry action. */
export function ErrorBlock({
  message,
  onRetry,
  retryLabel = 'Try again',
}: {
  message: string
  onRetry?: () => void
  retryLabel?: string
}) {
  return (
    <div role="alert" className="rounded-lg border border-danger bg-danger-bg px-3 py-2">
      <p className="text-sm text-danger">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded-lg border border-danger px-3 py-1 text-xs font-medium text-danger hover:bg-danger-bg focus:outline-none focus:ring-2 focus:ring-accent"
        >
          {retryLabel}
        </button>
      ) : null}
    </div>
  )
}

/**
 * One dashboard section: a semantic heading + its own body.
 *
 * Each section owns its state so ONE failing API call cannot take the whole
 * dashboard down — the other sections keep rendering their own data.
 */
export function SectionCard({
  title,
  headingId,
  children,
  action,
}: {
  title: string
  headingId: string
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <section aria-labelledby={headingId} className="rounded-xl border border-line bg-surface p-4 sm:p-5">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        <h2 id={headingId} className="min-w-0 flex-1 break-words font-semibold text-content text-section">
          {title}
        </h2>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      <div className="mt-3">{children}</div>
    </section>
  )
}

/** A labelled value inside the identity / academic-context definitions. */
export function Definition({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium break-words text-content">{value}</dd>
    </div>
  )
}

/** The em dash used wherever the backend genuinely has no value for a field. */
export const NOT_PROVIDED = '—'
