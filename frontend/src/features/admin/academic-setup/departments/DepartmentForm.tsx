import { useEffect, useRef } from 'react'
import type { DepartmentEditor } from './useDepartmentEditor.ts'

export default function DepartmentForm({ editor }: { editor: DepartmentEditor }) {
  const ref = useRef<HTMLFormElement>(null)
  const { draft, errors, change } = editor
  useEffect(() => {
    ref.current?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus()
  }, [editor.validationVersion])
  return (
    <form
      id="department-form"
      ref={ref}
      aria-label={editor.panel === 'edit' ? 'Edit department' : 'New department'}
      noValidate
      onSubmit={(event) => {
        event.preventDefault()
        editor.submit()
      }}
    >
      <p className="department-required-note">
        <span aria-hidden="true">*</span> Required fields
      </p>
      <fieldset disabled={editor.saving || !editor.canManage}>
        <label htmlFor="department-name">
          Department Name <span aria-hidden="true">*</span>
        </label>
        <input
          id="department-name"
          name="name"
          required
          autoFocus
          maxLength={160}
          value={draft.name}
          placeholder="Enter department name"
          onChange={(event) => change('name', event.target.value)}
          aria-invalid={Boolean(errors.name)}
          aria-describedby={errors.name ? 'department-name-error' : undefined}
        />
        {errors.name && (
          <p id="department-name-error" className="department-field-error">
            {errors.name}
          </p>
        )}
        <label htmlFor="department-code">
          Department Code <span aria-hidden="true">*</span>
        </label>
        <input
          id="department-code"
          name="code"
          required
          maxLength={32}
          value={draft.code}
          placeholder="Enter department code"
          onChange={(event) => change('code', event.target.value)}
          onBlur={() => {
            if (draft.code !== draft.code.trim()) change('code', draft.code.trim())
          }}
          aria-invalid={Boolean(errors.code)}
          aria-describedby={errors.code ? 'department-code-error' : 'department-code-help'}
        />
        {errors.code ? (
          <p id="department-code-error" className="department-field-error">
            {errors.code}
          </p>
        ) : (
          <p id="department-code-help" className="department-field-help">
            Up to 32 characters. Surrounding spaces are removed.
          </p>
        )}
        <label htmlFor="department-description">
          Description <small>(optional)</small>
        </label>
        <textarea
          id="department-description"
          name="description"
          rows={4}
          maxLength={2000}
          value={draft.description}
          placeholder="Enter department description"
          onChange={(event) => change('description', event.target.value)}
          aria-invalid={Boolean(errors.description)}
          aria-describedby={errors.description ? 'department-description-error' : 'department-description-help'}
        />
        {errors.description ? (
          <p id="department-description-error" className="department-field-error">
            {errors.description}
          </p>
        ) : (
          <p id="department-description-help" className="department-field-help">
            A brief description of the department.
          </p>
        )}
        <fieldset
          className="department-status-options"
          aria-describedby={errors.is_active ? 'department-status-error' : undefined}
        >
          <legend>
            Status <span aria-hidden="true">*</span>
          </legend>
          {[true, false].map((active) => (
            <label key={String(active)} className={draft.is_active === active ? 'is-selected' : undefined}>
              <input
                type="radio"
                name="department-status"
                required
                value={String(active)}
                checked={draft.is_active === active}
                onChange={() => change('is_active', active)}
                aria-invalid={Boolean(errors.is_active)}
              />
              <span>
                <strong>{active ? 'Active' : 'Inactive'}</strong>
                <small>
                  {active ? 'Marked active for this institution.' : 'Marked inactive; existing records are retained.'}
                </small>
              </span>
            </label>
          ))}
        </fieldset>
        {errors.is_active && (
          <p id="department-status-error" className="department-field-error">
            {errors.is_active}
          </p>
        )}
      </fieldset>
    </form>
  )
}
