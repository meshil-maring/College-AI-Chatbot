import type { ReactNode } from 'react'
import type { QuickSetupState } from './useQuickSetup.ts'

interface FrameProps {
  setup: QuickSetupState
  title: string
  description: string
  children: ReactNode
  onBack?: () => void
  continueLabel: string
  continueDisabled?: boolean
  onContinue: () => void
}

/** Shared step layout: heading, step error, content and Back / Continue actions. */
export function StepFrame({ setup, title, description, children, onBack, continueLabel, ...action }: FrameProps) {
  return (
    <section className="quick-step" aria-labelledby="quick-step-title" aria-busy={setup.saving}>
      <header>
        <h2 id="quick-step-title" tabIndex={-1}>
          {title}
        </h2>
        <p>{description}</p>
      </header>
      {setup.error && (
        <p className="quick-step-error" role="alert">
          {setup.error}
        </p>
      )}
      <div className="quick-step-body">{children}</div>
      <footer>
        {onBack && (
          <button type="button" className="academic-secondary-button" disabled={setup.saving} onClick={onBack}>
            Back
          </button>
        )}
        <button
          type="button"
          className="academic-primary-button"
          disabled={setup.saving || action.continueDisabled}
          onClick={action.onContinue}
        >
          {setup.saving ? 'Saving…' : continueLabel}
        </button>
      </footer>
    </section>
  )
}

/** "Use an existing record" or "Create a new one". */
export function ModeChoice({
  name,
  mode,
  hasExisting,
  noun,
  onChange,
}: {
  name: string
  mode: 'existing' | 'new'
  hasExisting: boolean
  noun: string
  onChange: (mode: 'existing' | 'new') => void
}) {
  return (
    <fieldset className="quick-mode">
      <legend className="sr-only">Choose or create a {noun}</legend>
      <label>
        <input
          type="radio"
          name={name}
          checked={mode === 'existing'}
          disabled={!hasExisting}
          onChange={() => onChange('existing')}
        />
        Use an existing {noun}
      </label>
      <label>
        <input type="radio" name={name} checked={mode === 'new'} onChange={() => onChange('new')} />
        Create a new {noun}
      </label>
    </fieldset>
  )
}

export function TextField({
  label,
  value,
  onChange,
  type = 'text',
  help,
  ...input
}: {
  label: string
  value: string
  onChange: (value: string) => void
  type?: 'text' | 'number' | 'date'
  help?: string
  min?: number
  max?: number
  step?: number | 'any'
  placeholder?: string
}) {
  return (
    <label className="quick-field">
      <span>{label}</span>
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} {...input} />
      {help && <small>{help}</small>}
    </label>
  )
}

export function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (value: string) => void
}) {
  return (
    <label className="quick-field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Select…</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}
