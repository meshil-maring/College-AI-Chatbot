import { useEffect, useRef } from 'react'
import { Save } from 'lucide-react'
import type { ResourceRevision } from '../../../types/learningResources.ts'
import type { ResourceContext } from '../data/resourceIdentity.ts'
import type { ResourceActions } from '../data/useResourceActions.ts'
import AudienceFields from './AudienceFields.tsx'
import { useResourceEditor } from './useResourceEditor.ts'

const types = [
  ['handbook', 'Handbook'],
  ['policy', 'Policy'],
  ['circular', 'Circular'],
  ['regulation', 'Regulation'],
  ['syllabus', 'Syllabus'],
  ['other', 'Other material'],
]
export default function ResourceEditor({
  context,
  revision,
  actions,
  disabled,
  onSaved,
  onDirty,
}: {
  context: ResourceContext
  revision?: ResourceRevision
  actions: ResourceActions
  disabled: boolean
  onSaved: (revision: ResourceRevision) => void
  onDirty: (dirty: boolean) => void
}) {
  const editor = useResourceEditor(context, revision, actions, onSaved, onDirty)
  const { draft, errors, change } = editor
  const form = useRef<HTMLFormElement>(null)
  const busy = disabled || actions.saving || actions.blocked
  useEffect(() => {
    form.current?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus()
  }, [errors])
  return (
    <form
      ref={form}
      className="lr-form"
      noValidate
      onSubmit={(event) => {
        event.preventDefault()
        if (!busy) void editor.save()
      }}
    >
      <fieldset disabled={busy}>
        <legend className="lr-section-title">Resource details</legend>
        <label htmlFor="resource-title">
          Title <span aria-hidden="true">*</span>
        </label>
        <input
          id="resource-title"
          value={draft.title}
          required
          maxLength={200}
          aria-invalid={Boolean(errors.title)}
          aria-describedby={errors.title ? 'resource-title-error' : undefined}
          onChange={(event) => change('title', event.target.value)}
          placeholder="e.g. Library borrowing guide"
        />
        {errors.title && (
          <p id="resource-title-error" className="lr-field-error">
            {errors.title}
          </p>
        )}
        <label htmlFor="resource-type">
          Resource type <span aria-hidden="true">*</span>
        </label>
        <select
          id="resource-type"
          value={draft.source_type}
          onChange={(event) => change('source_type', event.target.value)}
        >
          {!types.some(([value]) => value === draft.source_type) && (
            <option value={draft.source_type}>{draft.source_type}</option>
          )}
          {types.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <label htmlFor="resource-description">Description</label>
        <textarea
          id="resource-description"
          value={draft.description ?? ''}
          maxLength={5000}
          onChange={(event) => change('description', event.target.value)}
          placeholder="What does this resource help people understand?"
        />
        <div className="lr-date-fields">
          <label>
            Available from
            <input
              type="date"
              value={draft.effective_from ?? ''}
              onChange={(event) => change('effective_from', event.target.value)}
            />
          </label>
          <label>
            Available until
            <input
              type="date"
              value={draft.effective_until ?? ''}
              aria-invalid={Boolean(errors.effective_until)}
              aria-describedby={errors.effective_until ? 'resource-date-error' : undefined}
              onChange={(event) => change('effective_until', event.target.value)}
            />
          </label>
        </div>
        {errors.effective_until && (
          <p id="resource-date-error" className="lr-field-error">
            {errors.effective_until}
          </p>
        )}
      </fieldset>
      <AudienceFields value={draft.audience} disabled={busy} onChange={(audience) => change('audience', audience)} />
      <div className="lr-form-footer">
        <p className="lr-help">
          {revision
            ? 'Save any detail changes before uploading or submitting.'
            : 'Save your private draft first, then attach and index files.'}
        </p>
        <button type="submit" className="ui-primary" disabled={busy || Boolean(revision && !editor.dirty)}>
          <Save size={16} aria-hidden="true" />
          {actions.saving && actions.activity === 'save' ? 'Saving…' : 'Save draft'}
        </button>
      </div>
    </form>
  )
}
