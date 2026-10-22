import AcademicSetupHelp from '../AcademicSetupHelp.tsx'
import { ACADEMIC_DEFINITIONS } from '../academicSetupDefinitions.ts'
import { records, usable, label } from '../academicSetupModel.ts'
import type { AcademicSetupState } from '../useAcademicSetup.ts'

const inputClass = 'academic-input'
export default function AcademicRecordForm({ state }: { state: AcademicSetupState }) {
  const {
    data,
    entity,
    definition,
    editing,
    department,
    setDepartment,
    setForm,
    form,
    busy,
    save,
    change,
    choices,
    fieldHint,
    missing,
    setFormOpen,
  } = state
  if (!data) return null
  return (
    <form onSubmit={(event) => void save(event)} className="mt-5 space-y-4 rounded-xl border border-slate-600 p-4">
      <h3 className="font-semibold">{editing ? 'Edit record' : 'New record'}</h3>
      <p className="text-xs text-slate-400">Fields marked * are required. Other fields can be left blank.</p>
      {editing ? (
        <p className="text-xs text-slate-400">
          Academic relationships are fixed after creation. Deactivation preserves dependent records and history.
        </p>
      ) : null}
      {!editing && ['program_courses', 'course_offerings'].includes(entity) ? (
        <div className="text-sm">
          <div className="flex items-center gap-1">
            <label htmlFor="academic-department-filter">Program department filter</label>
            <AcademicSetupHelp label="Program department filter">
              Optionally narrow the program list to one department. This does not restrict which department a subject
              belongs to.
            </AcademicSetupHelp>
          </div>
          <select
            id="academic-department-filter"
            disabled={busy}
            value={department}
            onChange={(event) => {
              setDepartment(event.target.value)
              setForm((previous) => ({ ...previous, program_id: '', course_id: '' }))
            }}
            className={inputClass}
          >
            <option value="">All active departments</option>
            {records(data, 'departments')
              .filter((row) => usable(data, 'departments', row))
              .map((row) => (
                <option key={String(row.department_id)} value={String(row.department_id)}>
                  {label(data, 'departments', row)}
                </option>
              ))}
          </select>
        </div>
      ) : null}
      <fieldset disabled={busy} className="grid gap-4 md:grid-cols-2">
        {definition.fields.map((field) => {
          const id = `academic-${entity}-${field.key}`
          const hint = fieldHint(field)
          const describedBy = `${id}-help${hint ? ` ${id}-hint` : ''}`
          return (
            <div key={field.key} className="min-w-0 text-sm">
              <div className="flex items-center gap-1">
                <label htmlFor={id}>
                  {field.label}
                  {field.required ? ' *' : ''}
                </label>
                <AcademicSetupHelp label={field.label}>{field.help}</AcademicSetupHelp>
                {field.type === 'checkbox' ? (
                  <input
                    id={id}
                    aria-describedby={describedBy}
                    type="checkbox"
                    checked={Boolean(form[field.key])}
                    disabled={field.key === 'is_current' && !form.is_active}
                    onChange={(event) => change(field, event.target.checked)}
                    className="ml-2 accent-emerald-500"
                  />
                ) : null}
              </div>
              <span id={`${id}-help`} className="sr-only">
                {field.help}
              </span>
              {field.source || field.options ? (
                <select
                  id={id}
                  aria-describedby={describedBy}
                  required={field.required}
                  disabled={Boolean(editing && field.immutable)}
                  value={String(form[field.key] ?? '')}
                  onChange={(event) => change(field, event.target.value)}
                  className={inputClass}
                >
                  <option value="">{field.required ? `Select ${field.label.toLowerCase()}` : 'Any semester'}</option>
                  {field.source
                    ? choices(field).map((row) => (
                        <option
                          key={String(row[ACADEMIC_DEFINITIONS[field.source!].id])}
                          value={String(row[ACADEMIC_DEFINITIONS[field.source!].id])}
                        >
                          {label(data, field.source!, row)}
                        </option>
                      ))
                    : field.options?.map((option) => (
                        <option key={option} value={option}>
                          {option.replaceAll('_', ' ')}
                        </option>
                      ))}
                </select>
              ) : field.type === 'textarea' ? (
                <textarea
                  id={id}
                  aria-describedby={describedBy}
                  maxLength={4000}
                  placeholder={field.placeholder}
                  value={String(form[field.key] ?? '')}
                  onChange={(event) => change(field, event.target.value)}
                  className={inputClass}
                />
              ) : field.type !== 'checkbox' ? (
                <input
                  id={id}
                  aria-describedby={describedBy}
                  required={field.required}
                  maxLength={field.type ? undefined : 200}
                  placeholder={field.placeholder}
                  disabled={Boolean(editing && field.immutable)}
                  type={field.type ?? 'text'}
                  min={field.min}
                  step={
                    field.type === 'number'
                      ? ['capacity', 'semester_number', 'start_year', 'end_year'].includes(field.key)
                        ? '1'
                        : '0.01'
                      : undefined
                  }
                  value={String(form[field.key] ?? '')}
                  onChange={(event) => change(field, event.target.value)}
                  className={inputClass}
                />
              ) : null}
              {hint ? (
                <p id={`${id}-hint`} className="mt-2 text-xs text-amber-200">
                  {hint}
                </p>
              ) : null}
            </div>
          )
        })}
        <div className="text-sm">
          <div className="flex items-center gap-1">
            <label htmlFor="academic-is-active">Active</label>
            <AcademicSetupHelp label="Active">
              Keep checked to make this record available in later steps. Unchecking retains the record and its history,
              but makes it and dependent records unavailable for new selections.
            </AcademicSetupHelp>
            <input
              id="academic-is-active"
              type="checkbox"
              checked={Boolean(form.is_active)}
              onChange={(event) => change({ key: 'is_active' }, event.target.checked)}
              className="ml-2 accent-emerald-500"
            />
          </div>
        </div>
      </fieldset>
      <div className="flex gap-3">
        <button
          disabled={busy || (!editing && missing.length > 0)}
          type="submit"
          className="rounded-lg bg-emerald-700 px-4 py-2 text-sm disabled:opacity-50"
        >
          {busy ? 'Saving…' : 'Save record'}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => setFormOpen(false)}
          className="rounded-lg border border-slate-600 px-4 py-2 text-sm"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
