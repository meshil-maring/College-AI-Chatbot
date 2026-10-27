import { ChevronDown, ChevronRight, Plus } from 'lucide-react'
import CalendarActions, { CalendarBadge } from './CalendarActions.tsx'
import CalendarSemesters from './CalendarSemesters.tsx'
import { formatCalendarDate } from './calendarModel.ts'
import type { CalendarState } from './useCalendar.ts'
import type { CalendarEditor } from './useCalendarEditor.ts'

export default function CalendarYears({ state, editor }: { state: CalendarState; editor: CalendarEditor }) {
  return (
    <div className="calendar-years">
      <div className="calendar-year-heading" aria-hidden="true">
        {['Academic Year', 'Code', 'Start Date', 'End Date', 'Semesters', 'Status', 'Actions'].map((label) => (
          <span key={label}>{label}</span>
        ))}
      </div>
      {state.yearRows.map((year) => {
        const expanded = Boolean(state.isExpanded(year.academic_year_id))
        const semesters = state.semesters
          ?.filter((semester) => semester.academic_year_id === year.academic_year_id)
          .sort((a, b) => a.semester_number - b.semester_number)
        const Icon = expanded ? ChevronDown : ChevronRight
        return (
          <article
            className={`calendar-year-card${expanded ? ' is-expanded' : ''}`}
            key={year.academic_year_id}
            aria-label={year.name}
          >
            <div className="calendar-year-row">
              <button
                type="button"
                className="calendar-year-title"
                aria-expanded={expanded}
                aria-controls={`calendar-year-${year.academic_year_id}`}
                onClick={() => state.toggle(year.academic_year_id, expanded)}
              >
                <Icon aria-hidden="true" />
                <span>
                  <strong>
                    {year.name} {year.is_current && <small className="calendar-current">Current</small>}
                  </strong>
                  <small>Academic Year {year.name}</small>
                </span>
              </button>
              <span data-label="Code">{year.code}</span>
              <span data-label="Start Date">{formatCalendarDate(year.start_date)}</span>
              <span data-label="End Date">{formatCalendarDate(year.end_date)}</span>
              <span data-label="Semesters">{semesters?.length ?? 'Unavailable'}</span>
              <span data-label="Status">
                <CalendarBadge period={year} />
              </span>
              <CalendarActions record={year} editor={editor} canEdit={state.canManageYears && !state.busy} />
            </div>
            {expanded && (
              <div className="calendar-year-contents" id={`calendar-year-${year.academic_year_id}`}>
                {semesters ? (
                  <CalendarSemesters records={semesters} state={state} editor={editor} />
                ) : (
                  <p className="calendar-inline-empty">Semester records are unavailable for your account.</p>
                )}
                <div className="calendar-year-footer">
                  <button
                    type="button"
                    className="calendar-outline-button"
                    disabled={!state.canManageSemesters || state.busy || !year.is_active || editor.saving}
                    onClick={() => editor.open('semesters', 'add', undefined, year)}
                  >
                    <Plus aria-hidden="true" /> Add Semester
                  </button>
                </div>
              </div>
            )}
          </article>
        )
      })}
    </div>
  )
}
