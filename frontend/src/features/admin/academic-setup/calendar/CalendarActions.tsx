import { Eye, Pencil, Trash2 } from 'lucide-react'
import { periodStatus, type CalendarPeriod } from './calendarModel.ts'
import type { CalendarEditor } from './useCalendarEditor.ts'
import type { CalendarDeletion } from './useCalendarDeletion.ts'

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
  deletion,
}: {
  record: CalendarPeriod
  editor: CalendarEditor
  canEdit: boolean
  deletion: CalendarDeletion
}) {
  const entity = 'semester_id' in record ? 'semesters' : 'academic_years'
  return (
    <div className="calendar-record-actions">
      <button
        type="button"
        aria-label={`View ${record.name}`}
        disabled={editor.saving || deletion.saving}
        onClick={() => editor.open(entity, 'view', record)}
      >
        <Eye aria-hidden="true" />
      </button>
      <button
        type="button"
        aria-label={`Edit ${record.name}`}
        disabled={!canEdit || editor.saving || deletion.saving}
        onClick={() => editor.open(entity, 'edit', record)}
      >
        <Pencil aria-hidden="true" />
      </button>
      {deletion.canManage(record) && (
        <button
          type="button"
          aria-label={`Delete ${record.name}`}
          title="Delete unused record"
          disabled={editor.saving || deletion.saving}
          onClick={() => deletion.open(record)}
        >
          <Trash2 aria-hidden="true" />
        </button>
      )}
    </div>
  )
}
