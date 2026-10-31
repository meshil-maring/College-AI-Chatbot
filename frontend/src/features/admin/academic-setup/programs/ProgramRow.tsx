import { Eye, MoreHorizontal, Pencil, Power, Trash2 } from 'lucide-react'
import type { DegreeProgram, Department } from '../../../../types/academicSetup.ts'

export function ProgramBadge({ active }: { active: boolean }) {
  return (
    <span className={`program-badge${active ? ' is-active' : ''}`}>
      <span aria-hidden="true" />
      {active ? 'Active' : 'Inactive'}
    </span>
  )
}
interface Props {
  record: DegreeProgram
  index: number
  department?: Department
  editable: boolean
  canDelete: boolean
  onDelete: (record: DegreeProgram) => void
  onOpen: (mode: 'view' | 'edit', record: DegreeProgram) => void
  onStatus: (record: DegreeProgram) => void
}
export default function ProgramRow({
  record,
  index,
  department,
  editable,
  canDelete,
  onDelete,
  onOpen,
  onStatus,
}: Props) {
  return (
    <tr>
      <td data-label="Program Name">
        <div className="program-identity">
          <span className={`program-avatar tone-${index % 8}`} aria-hidden="true">
            {record.name
              .replace(/^(B|M)\.?\s*(Tech|Sc|Com|A)\s*/i, '')
              .slice(0, 1)
              .toLocaleUpperCase() || record.name.slice(0, 1)}
          </span>
          <div>
            <strong>{record.name}</strong>
            {record.description && <p>{record.description}</p>}
          </div>
        </div>
      </td>
      <td data-label="Code">{record.code}</td>
      <td data-label="Department">
        <span title={department?.name}>{department?.code ?? 'Unavailable'}</span>
      </td>
      <td data-label="Degree Type">{record.degree_type}</td>
      <td data-label="Duration">
        {record.duration_years} {record.duration_years === 1 ? 'Year' : 'Years'}
      </td>
      <td data-label="Credits">{record.total_credits ?? '—'}</td>
      <td data-label="Status">
        <ProgramBadge active={record.is_active} />
      </td>
      <td data-label="Actions">
        <div className="program-row-actions">
          <button
            type="button"
            onClick={() => onOpen('view', record)}
            aria-label={`View ${record.name}`}
            title="View details"
          >
            <Eye aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={() => onOpen('edit', record)}
            aria-label={`Edit ${record.name}`}
            title={editable ? 'Edit program' : 'Read-only access'}
            disabled={!editable}
          >
            <Pencil aria-hidden="true" />
          </button>
          {canDelete && (
            <button
              type="button"
              onClick={() => onDelete(record)}
              aria-label={`Delete ${record.name}`}
              title="Delete unused program"
              disabled={!editable}
            >
              <Trash2 aria-hidden="true" />
            </button>
          )}
          <details
            className="program-more"
            onKeyDown={(event) => {
              if (event.key === 'Escape') {
                event.currentTarget.open = false
                event.currentTarget.querySelector('summary')?.focus()
              }
            }}
          >
            <summary aria-label={`More actions for ${record.name}`} title="More actions">
              <MoreHorizontal aria-hidden="true" />
            </summary>
            <div>
              <button
                type="button"
                disabled={!editable}
                onClick={(event) => {
                  event.currentTarget.closest('details')?.removeAttribute('open')
                  onStatus(record)
                }}
              >
                <Power aria-hidden="true" />
                {record.is_active ? 'Deactivate program' : 'Activate program'}
              </button>
            </div>
          </details>
        </div>
      </td>
    </tr>
  )
}
