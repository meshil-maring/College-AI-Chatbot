import type { Course, Department } from '../../../../types/academicSetup.ts'
import { SubjectBadge } from './SubjectRow.tsx'
import { assignmentLabels } from './subjectModel.ts'
import { COURSE_TYPE_LABELS as SUBJECT_TYPES } from '../forms/academicCourseTypes.ts'
import type { SubjectsState } from './useSubjects.ts'

export default function SubjectDetails({
  record,
  departments,
  assignments,
}: {
  record: Course
  departments?: Department[]
  assignments: SubjectsState['assignments']
}) {
  const department = departments?.find((item) => item.department_id === record.department_id)
  const labels = assignmentLabels(record.course_id, assignments)
  const details = [
    ['Subject Code', record.code],
    ['Department', department ? `${department.name} (${department.code})` : 'Unavailable'],
    ['Semester', labels.semesters],
    [
      'Subject Type',
      labels.types?.map((type) => SUBJECT_TYPES[type]).join(', ') || (labels.types ? 'Unassigned' : 'Unavailable'),
    ],
    ['Credits', record.credits ?? 'Not specified'],
    ['Lecture Hours (L)', record.lecture_hours ?? 'Not specified'],
    ['Tutorial Hours (T)', record.tutorial_hours ?? 'Not specified'],
    ['Practical Hours (P)', record.practical_hours ?? 'Not specified'],
    ['Description', record.description || 'No description provided.'],
  ]
  return (
    <div className="subject-details">
      <h3>{record.name}</h3>
      <SubjectBadge active={record.is_active} />
      <dl>
        {details.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
