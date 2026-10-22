import type { FormEvent, ReactNode } from 'react'
import type {
  AcademicPackageCatalogue,
  PackageCollection,
  PackageOption,
  PackageRecord,
} from '../../../types/academicPackages.ts'
import { label, primaryKeys, rows, value } from '../packagePresentation.ts'

export function text(form: FormData, name: string) {
  return String(form.get(name) ?? '').trim()
}
export function number(form: FormData, name: string) {
  return Number(text(form, name))
}
export function checked(form: FormData, name: string) {
  return form.get(name) === 'on'
}

export function PackageForm({
  title,
  children,
  busy,
  onSave,
  submit = 'Save',
}: {
  title: string
  children: ReactNode
  busy: boolean
  submit?: string
  onSave: (form: FormData) => Promise<void>
}) {
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    try {
      await onSave(new FormData(form))
      form.reset()
    } catch {
      /* The workspace displays the mutation error. */
    }
  }
  return (
    <section className="academic-panel package-card">
      <h3>{title}</h3>
      <form className="package-form" onSubmit={(event) => void save(event)} aria-label={title}>
        <fieldset disabled={busy} className="package-form">
          {children}
          <button className="academic-primary" type="submit">
            {busy ? 'Saving…' : submit}
          </button>
        </fieldset>
      </form>
    </section>
  )
}

export function Select({
  data,
  source,
  name,
  title,
  items,
  selected,
  onChange,
  emptyHint,
}: {
  data: AcademicPackageCatalogue
  source: PackageCollection | PackageOption
  name: string
  title: string
  items?: PackageRecord[]
  selected?: string
  onChange?: (value: string) => void
  emptyHint?: string
}) {
  const options = (items ?? rows(data, source)).filter((row) => row.is_active !== false)
  return (
    <label>
      {title}
      <select
        name={name}
        aria-label={title}
        required
        value={selected}
        onChange={(event) => onChange?.(event.target.value)}
      >
        <option value="">Choose {title.toLowerCase()}</option>
        {options.map((row) => (
          <option key={value(row, primaryKeys[source])} value={value(row, primaryKeys[source])}>
            {label(data, source, row)}
          </option>
        ))}
      </select>
      {options.length === 0 && (
        <span className="package-helper">
          {emptyHint ?? 'No available records. Complete the preceding setup first.'}
        </span>
      )}
    </label>
  )
}

export function Input({
  name,
  title,
  type = 'text',
  max,
  defaultValue,
}: {
  name: string
  title: string
  type?: 'text' | 'number'
  max?: number
  defaultValue?: number
}) {
  return (
    <label>
      {title}
      <input
        name={name}
        aria-label={title}
        type={type}
        min={type === 'number' ? 1 : undefined}
        max={max}
        maxLength={name === 'section_code' ? 128 : name.includes('code') ? 64 : 200}
        defaultValue={defaultValue}
        required
      />
    </label>
  )
}

export function Checkbox({
  name,
  title,
  defaultChecked = false,
}: {
  name: string
  title: string
  defaultChecked?: boolean
}) {
  return (
    <label className="package-checkbox">
      <input name={name} aria-label={title} type="checkbox" defaultChecked={defaultChecked} />
      {title}
    </label>
  )
}

export function Reason() {
  return (
    <label>
      Reason
      <textarea
        name="reason"
        aria-label="Reason"
        maxLength={2000}
        required
        placeholder="Explain the requested change or decision"
      />
    </label>
  )
}
