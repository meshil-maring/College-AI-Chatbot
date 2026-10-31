import type { CurriculumSubject } from '../../../../../types/academicStructure.ts'
import type { AcademicStructureState } from '../../structure/useAcademicStructure.ts'
import { COURSE_TYPE_LABELS } from '../../forms/academicCourseTypes.ts'

function subjectDisplay(subject: CurriculumSubject, state: AcademicStructureState) {
  const version = state.structure?.records.curriculum_versions?.find(
    (item) => item.curriculum_version_id === subject.curriculum_version_id,
  )
  const published = version?.status === 'published'
  if (published && subject.subject_name) {
    return {
      code: subject.subject_code ?? '—',
      name: subject.subject_name,
      credits: subject.credits ?? '—',
      lecture: subject.lecture_hours ?? '—',
      tutorial: subject.tutorial_hours ?? '—',
      practical: subject.practical_hours ?? '—',
    }
  }
  const course = state.catalogue?.records.courses?.find((item) => item.course_id === subject.course_id)
  return {
    code: course?.code ?? '—',
    name: course?.name ?? 'Subject unavailable',
    credits: course?.credits ?? '—',
    lecture: course?.lecture_hours ?? '—',
    tutorial: course?.tutorial_hours ?? '—',
    practical: course?.practical_hours ?? '—',
  }
}

export default function SemesterSubjectList({
  state,
  subjects,
  semesterName,
  compulsory,
  showEdit,
  canEdit,
  onEdit,
}: {
  state: AcademicStructureState
  subjects: CurriculumSubject[]
  semesterName: string
  compulsory: boolean
  showEdit: boolean
  canEdit: boolean
  onEdit: (subject: CurriculumSubject) => void
}) {
  return (
    <section
      className="study-plan-subjects"
      aria-label={`${compulsory ? 'Compulsory subjects' : 'Subjects available for choices'} in ${semesterName}`}
    >
      <header className="study-plan-section-heading">
        <h4>{compulsory ? 'Compulsory subjects' : 'Subjects available for choices'}</h4>
      </header>
      {!subjects.length && (
        <p className="study-plan-empty">
          {compulsory ? 'No compulsory subjects yet.' : 'No subjects marked for student choices.'}
        </p>
      )}
      {subjects.length > 0 && (
        <ul className="study-plan-subject-list">
          {subjects.map((subject) => {
            const display = subjectDisplay(subject, state)
            return (
              <li key={subject.curriculum_subject_id}>
                <div>
                  <strong className="study-plan-subject-name">{display.name}</strong>
                  <p className="study-plan-subject-meta">
                    {display.code} · {COURSE_TYPE_LABELS[subject.course_type]} ·{' '}
                    {subject.is_required ? 'Compulsory' : 'Student choice'}
                    {!subject.is_active ? ' · Not included' : ''}
                    {display.credits !== '—' && ` · ${display.credits} credits`}
                  </p>
                </div>
                {showEdit && (
                  <button
                    type="button"
                    className="academic-secondary-button"
                    aria-label={`Edit ${display.name} in ${semesterName}`}
                    disabled={!canEdit}
                    onClick={() => onEdit(subject)}
                  >
                    Edit
                  </button>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
