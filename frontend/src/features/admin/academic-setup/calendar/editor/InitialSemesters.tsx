import { Plus, Trash2 } from 'lucide-react'
import type { CalendarEditor } from '../useCalendarEditor.ts'
import { makeSemesters } from './calendarDraft.ts'

export default function InitialSemesters({ editor }: { editor: CalendarEditor }) {
  const { draft, errors, progress } = editor
  function update(key: string, field: 'semester_number' | 'start_date' | 'end_date', value: string) {
    editor.change(
      'semesters',
      draft.semesters.map((semester) =>
        semester.key === key ? { ...semester, [field]: field === 'semester_number' ? Number(value) : value } : semester,
      ),
    )
  }
  return (
    <div className="calendar-initial-semesters">
      <fieldset className="calendar-semester-options" disabled={Boolean(progress.year)}>
        <legend>
          Number of Semesters <span>*</span>
        </legend>
        {(
          [
            ['2', '2 Semesters'],
            ['3', '3 Semesters (Trimester)'],
            ['custom', 'Custom'],
          ] as const
        ).map(([value, label]) => (
          <label key={value}>
            <input
              type="radio"
              name="calendar-semester-plan"
              value={value}
              checked={draft.plan === value}
              onChange={() => editor.change('plan', value)}
            />
            {label}
          </label>
        ))}
      </fieldset>
      <p className="calendar-field-help">Initial Semesters</p>
      <div
        className="calendar-semester-plan"
        aria-describedby={errors.semesters ? 'calendar-semesters-error' : undefined}
      >
        {draft.semesters.map((semester, index) => (
          <fieldset key={semester.key} className="calendar-planned-semester" disabled={index < progress.completed}>
            <legend>
              Semester {semester.semester_number}
              {index < progress.completed ? ' · Saved' : ''}
            </legend>
            <label>
              Number
              <input
                type="number"
                min="1"
                max="2147483647"
                step="1"
                value={semester.semester_number || ''}
                aria-invalid={Boolean(errors.semesters)}
                onChange={(event) => update(semester.key, 'semester_number', event.target.value)}
              />
            </label>
            <label>
              Start Date
              <input
                type="date"
                value={semester.start_date}
                min={draft.start_date}
                max={draft.end_date}
                aria-invalid={Boolean(errors.semesters)}
                onChange={(event) => update(semester.key, 'start_date', event.target.value)}
              />
            </label>
            <label>
              End Date
              <input
                type="date"
                value={semester.end_date}
                min={draft.start_date}
                max={draft.end_date}
                aria-invalid={Boolean(errors.semesters)}
                onChange={(event) => update(semester.key, 'end_date', event.target.value)}
              />
            </label>
            <button
              type="button"
              aria-label={`Remove initial semester ${index + 1}`}
              onClick={() => {
                editor.change('plan', 'custom')
                editor.change(
                  'semesters',
                  draft.semesters.filter((item) => item.key !== semester.key),
                )
              }}
            >
              <Trash2 aria-hidden="true" />
            </button>
          </fieldset>
        ))}
        {errors.semesters && (
          <p className="calendar-field-error" id="calendar-semesters-error">
            {errors.semesters}
          </p>
        )}
        <button
          type="button"
          className="calendar-add-planned"
          onClick={() => {
            const number = Math.max(0, ...draft.semesters.map((semester) => semester.semester_number)) + 1
            const next = makeSemesters(draft.start_date, draft.end_date, 1)[0]
            if (!next) return
            editor.change('plan', 'custom')
            editor.change('semesters', [...draft.semesters, { ...next, semester_number: number }])
          }}
        >
          <Plus aria-hidden="true" /> Add Another Semester
        </button>
      </div>
    </div>
  )
}
