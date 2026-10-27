import type { Semester } from '../../../../types/academicSetup.ts'
import CalendarActions, { CalendarBadge } from './CalendarActions.tsx'
import { formatCalendarDate, semesterType } from './calendarModel.ts'
import type { CalendarState } from './useCalendar.ts'
import type { CalendarEditor } from './useCalendarEditor.ts'

export default function CalendarSemesters({
  records,
  state,
  editor,
  showYear = false,
}: {
  records: Semester[]
  state: CalendarState
  editor: CalendarEditor
  showYear?: boolean
}) {
  return (
    <div className="calendar-semester-table-wrap">
      <table className="calendar-semester-table" aria-label="Semesters">
        <thead>
          <tr>
            <th scope="col">Semester</th>
            {showYear && <th scope="col">Academic Year</th>}
            <th scope="col">Type</th>
            <th scope="col">Start Date</th>
            <th scope="col">End Date</th>
            <th scope="col">Status</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {records.map((semester) => (
            <tr key={semester.semester_id}>
              <th scope="row">
                {semester.name}
                {semester.is_current && <small className="calendar-current">Current</small>}
              </th>
              {showYear && (
                <td data-label="Academic Year">
                  {state.years?.find((year) => year.academic_year_id === semester.academic_year_id)?.name ??
                    'Unavailable'}
                </td>
              )}
              <td data-label="Type">{semesterType(semester.semester_number)}</td>
              <td data-label="Start Date">{formatCalendarDate(semester.start_date)}</td>
              <td data-label="End Date">{formatCalendarDate(semester.end_date)}</td>
              <td data-label="Status">
                <CalendarBadge period={semester} />
              </td>
              <td>
                <CalendarActions record={semester} editor={editor} canEdit={state.canManageSemesters && !state.busy} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!records.length && <p className="calendar-inline-empty">No semesters configured for this academic year.</p>}
    </div>
  )
}
