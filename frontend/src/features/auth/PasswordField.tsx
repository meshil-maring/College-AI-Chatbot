/**
 * Phase 6.15.6 — accessible password input with a visibility toggle.
 *
 * Extracted from the four authentication forms (login, registration,
 * password reset, change password) so all of them expose the SAME password
 * behaviour: an explicitly associated <label>, an optional field-level error
 * wired through `aria-invalid` + `aria-describedby`, and a keyboard-operable
 * show/hide toggle.
 *
 * Security rules honoured here:
 * - The value lives only in the parent's React state — it is never written to
 *   localStorage/sessionStorage, never placed in a URL, and never logged.
 * - The toggle only changes the `type` attribute of ITS OWN input; it never
 *   reads, copies, or exports the plaintext value.
 * - The toggle's accessible name ("Show current password" / "Hide …") lets
 *   assistive-technology users tell several password fields apart, and the
 *   visible text ("Show"/"Hide") is contained in that name (WCAG 2.5.3).
 */

import { useState } from 'react'

/** Visual accent of the field, matching the surface it is rendered on. */
export type PasswordFieldAccent = 'emerald' | 'amber'

export interface PasswordFieldProps {
  /** Visible label AND the input's accessible name (e.g. "New password"). */
  label: string
  /** Form control name (also the basis of the generated element ids). */
  name: string
  value: string
  onChange: (value: string) => void
  /** Field-level validation message; when set the field is marked invalid. */
  error?: string | null
  disabled?: boolean
  required?: boolean
  minLength?: number
  autoComplete?: 'current-password' | 'new-password'
  placeholder?: string
  accent?: PasswordFieldAccent
  onBlur?: () => void
}

const INPUT_BASE_CLASS =
  'min-w-0 flex-1 rounded-lg border bg-slate-900 px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-1'

const INPUT_ACCENT_CLASS: Record<PasswordFieldAccent, string> = {
  emerald: 'border-slate-600 focus:border-emerald-400 focus:ring-emerald-400',
  amber: 'border-slate-600 focus:border-amber-400 focus:ring-amber-400',
}

const TOGGLE_ACCENT_CLASS: Record<PasswordFieldAccent, string> = {
  emerald: 'border-slate-600 text-slate-200 hover:bg-slate-700 focus:ring-emerald-400',
  amber: 'border-amber-600/60 text-amber-300 hover:bg-slate-700 focus:ring-amber-400',
}

export default function PasswordField({
  label,
  name,
  value,
  onChange,
  error = null,
  disabled = false,
  required = false,
  minLength,
  autoComplete,
  placeholder,
  accent = 'emerald',
  onBlur,
}: PasswordFieldProps) {
  const [visible, setVisible] = useState(false)

  // Deterministic ids (same convention as the hand-written ids already used
  // by the auth screens) so the label, the error text, and the toggle all
  // reference the SAME input.
  const inputId = `${name}-input`
  const errorId = `${name}-error`

  return (
    <div className="flex flex-col gap-1 text-sm text-slate-300">
      <label htmlFor={inputId}>{label}</label>
      <div className="flex items-center gap-2">
        <input
          id={inputId}
          type={visible ? 'text' : 'password'}
          name={name}
          required={required}
          minLength={minLength}
          autoComplete={autoComplete}
          spellCheck={false}
          disabled={disabled}
          placeholder={placeholder}
          className={`${INPUT_BASE_CLASS} ${INPUT_ACCENT_CLASS[accent]}`}
          value={value}
          aria-invalid={error !== null ? true : undefined}
          aria-describedby={error !== null ? errorId : undefined}
          onChange={(event) => onChange(event.target.value)}
          onBlur={onBlur}
        />
        <button
          type="button"
          disabled={disabled}
          aria-controls={inputId}
          aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`}
          className={`shrink-0 rounded-lg border px-3 py-2 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:opacity-60 ${TOGGLE_ACCENT_CLASS[accent]}`}
          onClick={() => setVisible((current) => !current)}
        >
          {visible ? 'Hide' : 'Show'}
        </button>
      </div>
      {error !== null && (
        <p id={errorId} role="alert" className="text-sm text-red-400">
          {error}
        </p>
      )}
    </div>
  )
}
