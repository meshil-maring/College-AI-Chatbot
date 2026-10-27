import type { ReactNode } from 'react'

export default function CalendarField({
  id,
  label,
  required,
  error,
  help,
  children,
}: {
  id: string
  label: string
  required?: boolean
  error?: string
  help?: string
  children: ReactNode
}) {
  return (
    <div className="calendar-field">
      <label htmlFor={id}>
        {label}
        {required && <span> *</span>}
      </label>
      {children}
      {error && (
        <p id={`${id}-error`} className="calendar-field-error">
          {error}
        </p>
      )}
      {help && (
        <p id={`${id}-help`} className="calendar-field-help">
          {help}
        </p>
      )}
    </div>
  )
}
