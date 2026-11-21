import { X } from 'lucide-react'
import type { ReactNode } from 'react'
import type { MembershipRole } from '../../../types/admin.ts'

/** Shared look for Staff and Faculty Management: buttons, selects, badges and feedback. */
export const BUTTON_CLASS =
  'inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-control bg-raised px-3 py-2 text-sm font-semibold text-content hover:bg-hover focus-visible:outline-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50'
export const PRIMARY_BUTTON_CLASS =
  'inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-accent bg-accent px-4 py-2 text-sm font-semibold text-ink hover:bg-accent-hover active:bg-accent-pressed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50'
export const DANGER_BUTTON_CLASS =
  'inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-danger bg-danger-bg px-3 py-2 text-sm font-semibold text-danger hover:underline focus-visible:outline-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50'
export const SELECT_CLASS =
  'min-h-10 rounded-lg border border-control bg-surface px-3 py-2 text-sm text-content focus:border-accent focus:outline-none disabled:cursor-not-allowed disabled:opacity-50'

export const ROLE_OPTIONS: readonly { value: MembershipRole; label: string }[] = [
  // Teachers are Faculty: there is no separate Teacher role.
  { value: 'faculty', label: 'Faculty (Teacher)' },
  { value: 'staff', label: 'Staff' },
]

export type BadgeTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'accent'

const TONES: Record<BadgeTone, string> = {
  success: 'bg-success-bg text-success',
  warning: 'bg-warning-bg text-warning',
  danger: 'bg-danger-bg text-danger',
  info: 'bg-info-bg text-info',
  neutral: 'bg-neutral-bg text-neutral',
  accent: 'border border-accent text-accent',
}

export function Badge({ tone, children }: { tone: BadgeTone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-sm px-2 py-1 text-xs font-medium ${TONES[tone]}`}>
      {children}
    </span>
  )
}

/** Account and request statuses use the design system's status colors, always with written text. */
export function statusTone(status: string): BadgeTone {
  if (status === 'active' || status === 'approved') return 'success'
  if (status === 'pending') return 'warning'
  if (status === 'rejected') return 'danger'
  return 'neutral'
}

export function StatusBadge({ status }: { status: string }) {
  const text = status ? status[0].toUpperCase() + status.slice(1) : 'Unknown'
  return <Badge tone={statusTone(status)}>{text}</Badge>
}

export function roleLabel(role: MembershipRole) {
  return role === 'staff' ? 'Staff' : 'Faculty (Teacher)'
}

/** Initials avatar; decorative because the name is always written beside it. */
export function Initials({ name }: { name: string }) {
  const letters =
    name
      .split(/[\s@._-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join('') || '?'
  return (
    <span
      aria-hidden="true"
      className="inline-flex size-9 shrink-0 items-center justify-center rounded-full bg-raised text-xs font-semibold text-content"
    >
      {letters}
    </span>
  )
}

export function formatDate(value: string | null) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

/**
 * Page-level result of the last action. It stays pinned to the top of the
 * workspace so the outcome of a roster change far down the page is visible.
 */
export function Feedback({
  error,
  success,
  onDismiss,
}: {
  error: string | null
  success: string | null
  onDismiss: () => void
}) {
  if (!error && !success) return null
  const isError = error !== null
  return (
    <div className="sticky top-2 z-10">
      <div
        role={isError ? 'alert' : 'status'}
        className={`flex items-start gap-3 rounded-lg border p-3 text-sm shadow-overlay ${
          isError ? 'border-danger bg-danger-bg text-danger' : 'border-success bg-success-bg text-success'
        }`}
      >
        <p className="mr-auto">{error ?? success}</p>
        <button
          type="button"
          aria-label="Dismiss message"
          onClick={onDismiss}
          className="-m-1 inline-flex size-8 shrink-0 items-center justify-center rounded-lg hover:bg-hover"
        >
          <X aria-hidden="true" className="size-4" />
        </button>
      </div>
    </div>
  )
}
