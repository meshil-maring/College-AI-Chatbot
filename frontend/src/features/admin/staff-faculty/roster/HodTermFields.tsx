import type { DepartmentHeadTerm } from '../../../../types/transfer.ts'

/** Today as an ISO date in UTC, the calendar the server checks terms against. */
export function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

/** Why a term cannot be saved, or null. Mirrors the server's rules. */
export function termError({ starts_on, planned_end_on }: DepartmentHeadTerm): string | null {
  const today = todayIso()
  if (!starts_on) return 'Choose the start date.'
  if (starts_on > today) return 'The start date cannot be in the future.'
  if (planned_end_on && planned_end_on < starts_on) return 'The planned end cannot be before the start.'
  if (planned_end_on && planned_end_on < today) return 'The planned end date has already passed.'
  return null
}

interface Props {
  id: string
  label: string
  term: DepartmentHeadTerm
  disabled: boolean
  /** Indent under a checkbox label (default), or align with other fields. */
  indent?: boolean
  onChange: (term: DepartmentHeadTerm) => void
}

/** Start and optional planned end of one Head of Department appointment. */
export default function HodTermFields({ id, label, term, disabled, indent = true, onChange }: Props) {
  const error = termError(term)
  const inputClass =
    'h-9 rounded-lg border border-line bg-surface px-2 text-sm text-content aria-[invalid=true]:border-danger'
  return (
    <fieldset className={`${indent ? 'ml-8 ' : ''}mt-1 grid gap-2 pb-2 sm:grid-cols-2`}>
      <legend className="sr-only">Term for {label}</legend>
      <label className="flex flex-col gap-1 text-xs text-muted">
        Starts on
        <input
          type="date"
          value={term.starts_on}
          max={todayIso()}
          disabled={disabled}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
          onChange={(event) => onChange({ ...term, starts_on: event.target.value })}
          className={inputClass}
        />
      </label>
      <label className="flex flex-col gap-1 text-xs text-muted">
        Planned end (optional)
        <input
          type="date"
          value={term.planned_end_on ?? ''}
          min={todayIso()}
          disabled={disabled}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
          onChange={(event) => onChange({ ...term, planned_end_on: event.target.value || null })}
          className={inputClass}
        />
      </label>
      {error ? (
        <span id={`${id}-error`} className="text-xs text-danger sm:col-span-2">
          {error}
        </span>
      ) : null}
    </fieldset>
  )
}
