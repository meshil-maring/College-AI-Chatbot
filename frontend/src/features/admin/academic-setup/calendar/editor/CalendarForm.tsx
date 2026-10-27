import { useEffect, useRef } from 'react'
import type { CalendarState } from '../useCalendar.ts'
import type { CalendarEditor } from '../useCalendarEditor.ts'
import CalendarField from './CalendarField.tsx'
import InitialSemesters from './InitialSemesters.tsx'

export default function CalendarForm({ editor, state }: { editor: CalendarEditor; state: CalendarState }) {
  const ref = useRef<HTMLFormElement>(null)
  const { panel, draft, errors } = editor
  const semester = panel?.entity === 'semesters'
  const view = panel?.mode === 'view'
  const noun = semester ? 'Semester' : 'Academic Year'
  useEffect(() => {
    if (editor.validationVersion)
      ref.current?.querySelector<HTMLElement>('[aria-invalid="true"]:not(:disabled)')?.focus()
  }, [editor.validationVersion])
  return (
    <form
      id="calendar-form"
      aria-label={`${view ? 'View' : panel?.mode === 'edit' ? 'Edit' : 'New'} ${noun.toLowerCase()}`}
      ref={ref}
      noValidate
      onSubmit={(event) => {
        event.preventDefault()
        void editor.submit()
      }}
    >
      <fieldset disabled={view || editor.saving || !editor.canManage}>
        <fieldset disabled={Boolean(editor.progress.year)}>
          {semester && (
            <CalendarField id="calendar-parent" label="Academic Year" required error={errors.academic_year_id}>
              <select
                id="calendar-parent"
                value={draft.academic_year_id}
                disabled={panel?.mode !== 'add'}
                aria-invalid={Boolean(errors.academic_year_id)}
                aria-describedby={errors.academic_year_id ? 'calendar-parent-error' : undefined}
                onChange={(event) => editor.change('academic_year_id', event.target.value)}
              >
                <option value="">Select academic year</option>
                {state.years
                  ?.filter((year) => year.is_active || year.academic_year_id === draft.academic_year_id)
                  .map((year) => (
                    <option key={year.academic_year_id} value={year.academic_year_id}>
                      {year.name}
                    </option>
                  ))}
              </select>
            </CalendarField>
          )}
          <CalendarField
            id="calendar-name"
            label={`${noun} Name`}
            required
            error={errors.name}
            help={semester ? 'e.g. Semester 1' : 'e.g. 2026 - 2027'}
          >
            <input
              id="calendar-name"
              value={draft.name}
              maxLength={160}
              required
              aria-invalid={Boolean(errors.name)}
              aria-describedby={errors.name ? 'calendar-name-error' : 'calendar-name-help'}
              onChange={(event) => editor.change('name', event.target.value)}
            />
          </CalendarField>
          <CalendarField
            id="calendar-code"
            label={`${noun} Code`}
            required
            error={errors.code}
            help={semester ? 'e.g. S1' : 'e.g. AY2026'}
          >
            <input
              id="calendar-code"
              value={draft.code}
              maxLength={32}
              required
              aria-invalid={Boolean(errors.code)}
              aria-describedby={errors.code ? 'calendar-code-error' : 'calendar-code-help'}
              onChange={(event) => editor.change('code', event.target.value)}
            />
          </CalendarField>
          {semester && (
            <CalendarField id="calendar-number" label="Semester Number" required error={errors.semester_number}>
              <input
                id="calendar-number"
                type="number"
                min="1"
                max="2147483647"
                step="1"
                value={draft.semester_number || ''}
                required
                aria-invalid={Boolean(errors.semester_number)}
                aria-describedby={errors.semester_number ? 'calendar-number-error' : undefined}
                onChange={(event) => editor.change('semester_number', Number(event.target.value))}
              />
            </CalendarField>
          )}
          <div className="calendar-form-dates">
            <CalendarField id="calendar-start" label="Start Date" required error={errors.start_date}>
              <input
                id="calendar-start"
                type="date"
                value={draft.start_date}
                required
                aria-invalid={Boolean(errors.start_date)}
                aria-describedby={errors.start_date ? 'calendar-start-error' : undefined}
                onChange={(event) => editor.change('start_date', event.target.value)}
              />
            </CalendarField>
            <CalendarField id="calendar-end" label="End Date" required error={errors.end_date}>
              <input
                id="calendar-end"
                type="date"
                value={draft.end_date}
                required
                aria-invalid={Boolean(errors.end_date)}
                aria-describedby={errors.end_date ? 'calendar-end-error' : undefined}
                onChange={(event) => editor.change('end_date', event.target.value)}
              />
            </CalendarField>
          </div>
          <CalendarField id="calendar-status" label="Status" error={errors.is_active}>
            <select
              id="calendar-status"
              aria-invalid={Boolean(errors.is_active)}
              aria-describedby={errors.is_active ? 'calendar-status-error' : undefined}
              value={draft.is_active ? 'active' : 'inactive'}
              onChange={(event) => editor.change('is_active', event.target.value === 'active')}
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </CalendarField>
          <label className="calendar-current-option">
            <input
              type="checkbox"
              checked={draft.is_current}
              aria-invalid={Boolean(errors.is_current)}
              onChange={(event) => editor.change('is_current', event.target.checked)}
            />
            Set as current {semester ? 'semester' : 'academic year'}
          </label>
          {errors.is_current && <p className="calendar-field-error">{errors.is_current}</p>}
        </fieldset>
        {!semester && panel?.mode === 'add' && state.canManageSemesters && <InitialSemesters editor={editor} />}
        {!semester && panel?.mode === 'add' && !state.canManageSemesters && (
          <p className="calendar-field-help">
            Your account can create academic years. Semester configuration requires semester management access.
          </p>
        )}
      </fieldset>
    </form>
  )
}
