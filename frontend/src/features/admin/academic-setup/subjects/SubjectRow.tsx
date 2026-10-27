import { Eye, MoreHorizontal, Pencil, Power } from 'lucide-react'
import type { Course, Department } from '../../../../types/academicSetup.ts'
import type { SubjectsState } from './useSubjects.ts'
import { assignmentLabels } from './subjectModel.ts'
import { COURSE_TYPE_LABELS as SUBJECT_TYPES } from '../forms/academicCourseTypes.ts'

export function SubjectBadge({ active }: { active: boolean }) {
  return (
    <span className={`subject-badge${active ? ' is-active' : ''}`}>
      <span aria-hidden="true" />
      {active ? 'Active' : 'Inactive'}
    </span>
  )
}
interface Props {
  record: Course
  index: number
  department?: Department
  assignments: SubjectsState['assignments']
  editable: boolean
  onOpen: (mode: 'view' | 'edit', record: Course) => void
  onStatus: (record: Course) => void
}
export default function SubjectRow({ record, index, department, assignments, editable, onOpen, onStatus }: Props) {
  const labels = assignmentLabels(record.course_id, assignments)
  return (
    <tr>
      <td data-label="Subject Code">
        <div className="subject-identity">
          <span className={`subject-avatar tone-${index % 8}`} aria-hidden="true">
            {record.name.slice(0, 1).toLocaleUpperCase()}
          </span>
          <span>{record.code}</span>
        </div>
      </td>
      <td data-label="Subject Name">{record.name}</td>
      <td data-label="Department">
        <span title={department?.name}>{department?.code ?? 'Unavailable'}</span>
      </td>
      <td data-label="Semester">{labels.semesters}</td>
      <td data-label="Type">
        {labels.types?.length
          ? labels.types.map((type) => (
              <span key={type} className={`subject-type ${type}`}>
                {SUBJECT_TYPES[type]}
              </span>
            ))
          : labels.types
            ? 'Unassigned'
            : 'Unavailable'}
      </td>
      <td data-label="Credits">{record.credits ?? '—'}</td>
      <td data-label="L">
        <span title="Lecture hours">{record.lecture_hours ?? '—'}</span>
      </td>
      <td data-label="T">
        <span title="Tutorial hours">{record.tutorial_hours ?? '—'}</span>
      </td>
      <td data-label="P">
        <span title="Practical hours">{record.practical_hours ?? '—'}</span>
      </td>
      <td data-label="Status">
        <SubjectBadge active={record.is_active} />
      </td>
      <td data-label="Actions">
        <div className="subject-row-actions">
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
            title={editable ? 'Edit subject' : 'Read-only access'}
            disabled={!editable}
          >
            <Pencil aria-hidden="true" />
          </button>
          <details
            className="subject-more"
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
                {record.is_active ? 'Deactivate subject' : 'Activate subject'}
              </button>
            </div>
          </details>
        </div>
      </td>
    </tr>
  )
}
