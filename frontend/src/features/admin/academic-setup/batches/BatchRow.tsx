import { Eye, MoreHorizontal, Pencil } from 'lucide-react'
import { batchStatuses, type BatchRecord, type BatchStatus } from './batchModel.ts'
import type { BatchesState } from './useBatches.ts'

export interface BatchActions {
  onOpen: (mode: 'view' | 'edit', record: BatchRecord, status?: BatchStatus) => void
}
export default function BatchRow({
  record,
  onOpen,
  state,
}: { record: BatchRecord; state: BatchesState } & BatchActions) {
  const program = state.programs.find((item) => item.id === record.programId)
  const curriculum = state.curricula.find((item) => item.id === record.curriculumId)
  return (
    <tr>
      <td>
        <div className="batch-identity">
          <span className={`batch-avatar ${program?.color ?? 'gold'}`} aria-hidden="true">
            {record.name.charAt(0)}
          </span>
          <div>
            <strong>{record.name}</strong>
            <small>
              {program?.name} ({record.startYear} - {record.endYear})
            </small>
          </div>
        </div>
      </td>
      <td data-label="Code">{record.code}</td>
      <td data-label="Program">{program?.name}</td>
      <td data-label="Academic Year">
        {state.years.find((year) => year.academic_year_id === record.academicYear)?.name ?? 'Unavailable'}
      </td>
      <td data-label="Curriculum Version">{curriculum?.version}</td>
      <td data-label="Student Count">{record.studentCount?.toLocaleString('en-IN') ?? 'Unavailable'}</td>
      <td data-label="Status">
        <span className={`batch-status ${record.status}`}>
          <span aria-hidden="true" />
          {batchStatuses.find((item) => item.value === record.status)?.label}
        </span>
      </td>
      <td>
        <div className="batch-row-actions">
          <button
            type="button"
            aria-label={`View ${record.name}`}
            title="View batch"
            onClick={() => onOpen('view', record)}
          >
            <Eye aria-hidden="true" />
          </button>
          <button
            type="button"
            aria-label={`Edit ${record.name}`}
            title="Edit batch"
            disabled={!state.canManage || state.write.saving}
            onClick={() => onOpen('edit', record)}
          >
            <Pencil aria-hidden="true" />
          </button>
          <details className="batch-more">
            <summary aria-label={`More actions for ${record.name}`} title="More actions">
              <MoreHorizontal aria-hidden="true" />
            </summary>
            <div aria-label={`Status actions for ${record.name}`}>
              {batchStatuses
                .filter((item) => item.value !== record.status)
                .map((item) => (
                  <button
                    type="button"
                    key={item.value}
                    disabled={!state.canManage || state.write.saving}
                    onClick={(event) => {
                      const menu = event.currentTarget.closest('details')
                      menu?.removeAttribute('open')
                      menu?.querySelector('summary')?.focus()
                      onOpen('edit', record, item.value)
                    }}
                  >
                    Mark {item.label}
                  </button>
                ))}
            </div>
          </details>
        </div>
      </td>
    </tr>
  )
}
