import { AlertCircle, RefreshCw, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

export const panelClass = 'min-w-0 rounded-xl border border-slate-700 bg-slate-800/60 p-4 shadow-sm sm:p-5'
export const controlClass = 'mt-1 block min-h-10 w-full min-w-0 rounded-lg border border-slate-600 bg-slate-950/60 px-3 py-2 text-sm text-white [color-scheme:dark] outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-400/30 disabled:cursor-not-allowed disabled:opacity-50'
const buttonBase = 'inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 disabled:cursor-not-allowed disabled:opacity-50'
export const buttonClass = `${buttonBase} border-slate-500 text-slate-100 hover:bg-slate-700/60`
export const primaryClass = `${buttonBase} border-emerald-600 bg-emerald-700 text-white hover:bg-emerald-600`
export const dangerClass = `${buttonBase} border-red-500/70 text-red-300 hover:bg-red-950/50`

export function PanelHeading({ id, icon: Icon, title, description, purple = false }: { id: string; icon: LucideIcon; title: string; description: string; purple?: boolean }) {
  return <div className="flex items-start gap-3">
    <span className={`flex size-12 shrink-0 items-center justify-center rounded-xl ${purple ? 'bg-violet-700' : 'bg-emerald-700'} text-white`}><Icon size={24} aria-hidden="true" /></span>
    <div className="min-w-0"><h2 id={id} className="text-lg font-bold text-white">{title}</h2><p className="mt-1 text-sm leading-relaxed text-slate-300">{description}</p></div>
  </div>
}

export function StateBadge({ state }: { state: string }) {
  const tone = state === 'active' ? 'border-emerald-700 bg-emerald-900/60 text-emerald-100' : state === 'scheduled' ? 'border-blue-700 bg-blue-900/50 text-blue-100' : 'border-slate-600 bg-slate-700/60 text-slate-200'
  return <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-medium capitalize ${tone}`}><span aria-hidden="true" className={`size-2 rounded-full ${state === 'active' ? 'bg-emerald-400' : 'bg-current'}`} />{state}</span>
}

export function requestMessage(cause: unknown): string {
  const status = typeof cause === 'object' && cause !== null && 'status' in cause ? cause.status : undefined
  const code = typeof cause === 'object' && cause !== null && 'code' in cause ? cause.code : undefined
  if (code === 'FACULTY_SCHEMA_UNAVAILABLE' || code === 'ACADEMIC_SCHEMA_UNAVAILABLE') return 'Assignments and responsibilities are unavailable until the database update is applied. Please contact your administrator.'
  if (status === 403) return 'You do not have permission to manage these records. Contact your institution administrator if you need access.'
  if (status === 401) return 'Your session has expired. Sign in again to continue.'
  const message = cause instanceof Error ? cause.message : ''
  if ((typeof status === 'number' && status >= 500) || /HTTP 5\d\d|traceback|stack trace|PGRST|SQLSTATE/i.test(message)) return 'The server could not complete this request. Your form entries have been kept. Retry loading to check the latest records.'
  if (cause instanceof TypeError) return 'The service could not be reached. Check your connection and try again.'
  return message || 'The request could not be completed. Please try again.'
}

export function RequestFeedback({ title, error, onRetry, retryLabel, busy }: { title: string; error: unknown; onRetry?: () => void; retryLabel?: string; busy?: boolean }) {
  return <div role="alert" className="flex flex-wrap items-center gap-3 rounded-lg border border-red-500/70 bg-red-950/40 p-3 text-red-200">
    <AlertCircle className="shrink-0" size={22} aria-hidden="true" />
    <div className="min-w-0 flex-1"><p className="text-sm font-semibold">{title}</p><p className="mt-1 text-sm leading-relaxed">{requestMessage(error)}</p></div>
    {onRetry ? <button type="button" className={buttonClass} disabled={busy} onClick={onRetry}><RefreshCw size={16} aria-hidden="true" />{retryLabel ?? 'Retry'}</button> : null}
  </div>
}

export function FieldError({ id, children }: { id: string; children?: ReactNode }) {
  return children ? <p id={id} role="alert" className="mt-1 text-sm text-red-300">{children}</p> : null
}

type TeachingValidity = { start_at?: string; assigned_at?: string; end_at?: string | null; is_active?: boolean; revoked_at?: string | null }

// Presentation follows the server's half-open validity rule; it grants no authority.
export function teachingState(row: TeachingValidity, now: number): string {
  if (row.revoked_at) return 'revoked'
  if (row.is_active === false) return 'disabled'
  const start = row.start_at || row.assigned_at
  const zoned = (value: string) => /(?:Z|[+-]\d{2}:\d{2})$/i.test(value) && Number.isFinite(Date.parse(value))
  if (!start || !zoned(start) || (row.end_at && (!zoned(row.end_at) || Date.parse(row.end_at) <= Date.parse(start)))) return 'unavailable'
  if (now < Date.parse(start)) return 'scheduled'
  if (row.end_at && now >= Date.parse(row.end_at)) return 'expired'
  return 'active'
}

export function teachingPeriod(row: TeachingValidity): string {
  const date = (value: string) => Number.isFinite(Date.parse(value)) ? new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'Date unavailable'
  const start = row.start_at || row.assigned_at
  return `${start ? date(start) : 'Start unavailable'} – ${row.end_at ? date(row.end_at) : 'No end date'}`
}

export function periodError(start: string, end: string, required = false): { start?: string; end?: string } {
  if (!start && required) return { start: 'Choose a start date and time.' }
  if (start && !Number.isFinite(new Date(start).getTime())) return { start: 'Enter a valid start date and time.' }
  if (end && !start) return { end: 'Choose a teaching start before setting an end date.' }
  if (end && (!Number.isFinite(new Date(end).getTime()) || new Date(end) <= new Date(start))) return { end: 'End must be later than the start. The end time is exclusive.' }
  return {}
}
