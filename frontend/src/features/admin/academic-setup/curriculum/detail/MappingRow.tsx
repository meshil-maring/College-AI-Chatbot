import { Pencil, Power } from 'lucide-react'
import type { Course, ProgramCourse } from '../../../../../types/academicSetup.ts'
import { COURSE_TYPE_LABELS } from '../../forms/academicCourseTypes.ts'
import CurriculumBadge from '../CurriculumBadge.tsx'

export default function MappingRow({
  link,
  course,
  editable,
  onEdit,
  onStatus,
}: {
  link: ProgramCourse
  course?: Course
  editable: boolean
  onEdit: (link: ProgramCourse) => void
  onStatus: (link: ProgramCourse) => void
}) {
  return (
    <tr>
      <td data-label="Code">{course?.code ?? '—'}</td>
      <td data-label="Subject Name">
        {course?.name ?? 'Subject unavailable'}
        {course && !course.is_active && <small className="curriculum-record-note">Inactive subject</small>}
      </td>
      <td data-label="Type">
        <span className={`curriculum-type ${link.course_type}`}>{COURSE_TYPE_LABELS[link.course_type]}</span>
        <small className="curriculum-record-note">{link.is_required ? 'Required' : 'Optional'}</small>
      </td>
      <td data-label="Lecture Hours">{course?.lecture_hours ?? '—'}</td>
      <td data-label="Tutorial Hours">{course?.tutorial_hours ?? '—'}</td>
      <td data-label="Practical Hours">{course?.practical_hours ?? '—'}</td>
      <td data-label="Credits">{course?.credits ?? '—'}</td>
      <td data-label="Mapping Status">
        <CurriculumBadge active={link.is_active} />
      </td>
      <td data-label="Actions">
        <div className="curriculum-row-actions">
          <button
            type="button"
            aria-label={`Edit mapping for ${course?.name ?? 'unavailable subject'}`}
            title="Edit mapping"
            disabled={!editable}
            onClick={() => onEdit(link)}
          >
            <Pencil aria-hidden="true" />
          </button>
          <button
            type="button"
            aria-label={`${link.is_active ? 'Deactivate' : 'Activate'} mapping for ${course?.name ?? 'unavailable subject'}`}
            title={link.is_active ? 'Deactivate mapping' : 'Activate mapping'}
            disabled={!editable}
            onClick={() => onStatus(link)}
          >
            <Power aria-hidden="true" />
          </button>
        </div>
      </td>
    </tr>
  )
}
