import { Eye, MoreHorizontal, Pencil } from 'lucide-react'
import { sectionLabel, type SectionRecord, type SectionStatus } from './sectionModel.ts'
import type { SectionsState } from './useSections.ts'

export interface SectionActions {
  onOpen: (mode: 'view' | 'edit', record: SectionRecord, status?: SectionStatus) => void
}
export default function SectionRow({
  record,
  onOpen,
  state,
}: { record: SectionRecord; state: SectionsState } & SectionActions) {
  const batch = state.batches.find((item) => item.id === record.batchId)
  const program = state.programs.find((item) => item.id === batch?.programId)
  const label = sectionLabel(record, state.batches)
  return (
    <tr>
      <td>
        <div className="section-identity">
          <span className={`section-avatar ${record.color}`} aria-hidden="true">
            {record.name.trim().slice(-1)}
          </span>
          <div>
            <strong>{record.name}</strong>
            <small>
              {batch?.name} - {record.name.replace(/^Section\s+/i, '')}
            </small>
          </div>
        </div>
      </td>
      <td data-label="Code">{record.code}</td>
      <td data-label="Batch">{batch?.name}</td>
      <td data-label="Program">{program?.name}</td>
      <td data-label="Academic Year">{batch?.academicYear}</td>
      <td data-label="Student Count">{record.studentCount?.toLocaleString('en-IN') ?? 'Unavailable'}</td>
      <td data-label="Status">
        <span className={`section-status ${record.status}`}>
          <span aria-hidden="true" />
          {record.status === 'active' ? 'Active' : 'Inactive'}
        </span>
      </td>
      <td>
        <div className="section-row-actions">
          <button
            type="button"
            aria-label={`View ${label}`}
            title="View section"
            onClick={() => onOpen('view', record)}
          >
            <Eye aria-hidden="true" />
          </button>
          <button
            type="button"
            aria-label={`Edit ${label}`}
            title="Edit section"
            disabled={!state.canManage || state.write.saving}
            onClick={() => onOpen('edit', record)}
          >
            <Pencil aria-hidden="true" />
          </button>
          <details className="section-more">
            <summary aria-label={`More actions for ${label}`} title="More actions">
              <MoreHorizontal aria-hidden="true" />
            </summary>
            <div aria-label={`Status actions for ${label}`}>
              <button
                type="button"
                disabled={!state.canManage || state.write.saving}
                onClick={(event) => {
                  const menu = event.currentTarget.closest('details')
                  menu?.removeAttribute('open')
                  menu?.querySelector('summary')?.focus()
                  onOpen('edit', record, record.status === 'active' ? 'inactive' : 'active')
                }}
              >
                Mark {record.status === 'active' ? 'Inactive' : 'Active'}
              </button>
            </div>
          </details>
        </div>
      </td>
    </tr>
  )
}
