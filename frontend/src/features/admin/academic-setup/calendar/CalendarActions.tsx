import { Eye, Pencil } from 'lucide-react'
import { periodStatus, type CalendarPeriod } from './calendarModel.ts'
import type { CalendarEditor } from './useCalendarEditor.ts'

export function CalendarBadge({ period }: { period: CalendarPeriod }) {
  const status = periodStatus(period)
  return (
    <span className={`calendar-badge ${status}`}>
      <span aria-hidden="true" />
      {status[0].toUpperCase() + status.slice(1)}
    </span>
  )
}

export default function CalendarActions({
  record,
  editor,
  canEdit,
}: {
  record: CalendarPeriod
  editor: CalendarEditor
  canEdit: boolean
}) {
  const entity = 'semester_id' in record ? 'semesters' : 'academic_years'
  return (
    <div className="calendar-record-actions">
      <button
        type="button"
        aria-label={`View ${record.name}`}
        disabled={editor.saving}
        onClick={() => editor.open(entity, 'view', record)}
      >
        <Eye aria-hidden="true" />
      </button>
      <button
        type="button"
        aria-label={`Edit ${record.name}`}
        disabled={!canEdit || editor.saving}
        onClick={() => editor.open(entity, 'edit', record)}
      >
        <Pencil aria-hidden="true" />
      </button>
    </div>
  )
}
