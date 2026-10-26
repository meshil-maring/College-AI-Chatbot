import type { AcademicCatalogue, AcademicEntity } from '../../../types/academicSetup.ts'
import type { AcademicFieldsProps } from './forms/academicFormControls.ts'
import { academicButtonClass, academicInputClass } from './forms/academicFormControls.ts'
import { ACADEMIC_FIELDS } from './forms/academicFieldDefinitions.ts'
import AcademicRelationFields from './forms/AcademicRelationFields.tsx'

interface Props extends AcademicFieldsProps {
  entity: AcademicEntity
  singular: string
  catalogue: AcademicCatalogue
  busy: boolean
  onSave: () => void
  onCancel: () => void
}
export default function AcademicSetupForm({
  entity,
  singular,
  editing,
  draft,
  setDraft,
  catalogue,
  busy,
  onSave,
  onCancel,
}: Props) {
  const named = entity !== 'program_courses' && entity !== 'course_offerings'
  const period = entity === 'academic_years' || entity === 'semesters'
  return (
    <form
      aria-label={`${editing ? 'Edit' : 'New'} ${singular}`}
      onSubmit={(event) => {
        event.preventDefault()
        onSave()
      }}
      className="space-y-4 rounded-xl border border-slate-600 bg-slate-800 p-4"
    >
      <h3 className="font-semibold text-white">
        {editing ? 'Edit' : 'New'} {singular}
      </h3>
      <fieldset disabled={busy} className="grid gap-4 sm:grid-cols-2">
        {named && (
          <>
            <label className="text-sm text-slate-200">
              Name
              <input
                required
                maxLength={160}
                value={draft.name}
                onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
                className={academicInputClass}
              />
            </label>
            <label className="text-sm text-slate-200">
              Code
              <input
                required
                disabled={editing && entity === 'sections'}
                maxLength={32}
                value={draft.code}
                onChange={(event) => setDraft((current) => ({ ...current, code: event.target.value }))}
                className={academicInputClass}
              />
            </label>
          </>
        )}
        {['departments', 'programs', 'courses'].includes(entity) && (
          <label className="text-sm text-slate-200 sm:col-span-2">
            Description (optional)
            <textarea
              maxLength={2000}
              value={draft.description}
              onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))}
              className={academicInputClass}
            />
          </label>
        )}
        <AcademicRelationFields
          entity={entity}
          catalogue={catalogue}
          draft={draft}
          setDraft={setDraft}
          editing={editing}
        />
        {ACADEMIC_FIELDS[entity].map((field) => (
          <label key={field.key} className="text-sm text-slate-200">
            {field.label}
            <input
              type={field.type ?? 'text'}
              required={field.required}
              min={field.min}
              step={field.step}
              value={draft[field.key]}
              onChange={(event) => setDraft((current) => ({ ...current, [field.key]: event.target.value }))}
              className={academicInputClass}
            />
          </label>
        ))}
        {entity === 'program_courses' && (
          <>
            <label className="text-sm text-slate-200">
              Course type
              <select
                required
                value={draft.course_type}
                onChange={(event) => setDraft((current) => ({ ...current, course_type: event.target.value }))}
                className={academicInputClass}
              >
                <option value="">Choose course type</option>
                {['core', 'elective', 'open_elective', 'skill', 'project'].map((type) => (
                  <option key={type} value={type}>
                    {type.replaceAll('_', ' ')}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-200">
              <input
                type="checkbox"
                checked={draft.is_required}
                onChange={(event) => setDraft((current) => ({ ...current, is_required: event.target.checked }))}
              />
              Required course
            </label>
          </>
        )}
        {period && (
          <label className="flex items-center gap-2 text-sm text-slate-200">
            <input
              type="checkbox"
              checked={draft.is_current}
              disabled={!draft.is_active}
              onChange={(event) => setDraft((current) => ({ ...current, is_current: event.target.checked }))}
            />
            Current {entity === 'semesters' ? 'semester' : 'academic year'}
          </label>
        )}
        <label className="flex items-center gap-2 text-sm text-slate-200">
          <input
            type="checkbox"
            checked={draft.is_active}
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                is_active: event.target.checked,
                is_current: event.target.checked ? current.is_current : false,
              }))
            }
          />
          Active
        </label>
      </fieldset>
      <div className="flex gap-2">
        <button type="submit" disabled={busy} className={`${academicButtonClass} bg-emerald-700`}>
          {busy ? 'Saving...' : 'Save'}
        </button>
        <button type="button" disabled={busy} onClick={onCancel} className={academicButtonClass}>
          Cancel
        </button>
      </div>
    </form>
  )
}
