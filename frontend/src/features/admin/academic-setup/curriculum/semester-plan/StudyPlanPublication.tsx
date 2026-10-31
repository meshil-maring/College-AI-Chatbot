import type { CurriculumVersion } from '../../../../../types/academicStructure.ts'
import type { AcademicStructureState } from '../../structure/useAcademicStructure.ts'
import CurriculumDrawerFrame from '../editor/CurriculumDrawerFrame.tsx'
import { useStudyPlanPublication } from './useStudyPlanPublication.ts'
import type { StudyPlanChoicesState } from './useStudyPlanChoices.ts'

function subjectName(subject: { course_id: string; subject_name?: string }, state: AcademicStructureState) {
  if (subject.subject_name) return subject.subject_name
  return state.catalogue?.records.courses?.find((course) => course.course_id === subject.course_id)?.name ??
    'Subject unavailable'
}

export default function StudyPlanPublication({
  state,
  version,
  onBatches,
  choices,
}: {
  state: AcademicStructureState
  version: CurriculumVersion
  onBatches?: () => void
  choices: StudyPlanChoicesState
}) {
  const publication = useStudyPlanPublication(state, version, choices)
  const { reviewing, notice, semesters, count, canPublish, saving } = publication
  return (
    <div className="study-plan-publication">
      {notice && <p role="status">{notice}</p>}
      {version.status === 'draft' ? (
        <>
          {!count && <p>Add at least one subject before publishing.</p>}
          {choices.busy && <p>Student choices must finish loading or saving before publishing.</p>}
          {choices.hasDrafts && <p>Save or cancel the open choice group before publishing.</p>}
          <button
            type="button"
            className="academic-primary-button"
            disabled={!canPublish || saving}
            onClick={publication.review}
          >
            Review and publish
          </button>
        </>
      ) : version.status === 'published' && onBatches ? (
        <button type="button" className="academic-primary-button" onClick={onBatches}>
          Assign to a batch
        </button>
      ) : null}
      {reviewing && (
        <CurriculumDrawerFrame
          title="Review study plan"
          description={`${version.name} · v${version.version}. Publishing keeps this study plan fixed for the batches using it.`}
          busy={saving}
          alert
          onClose={publication.close}
          footer={
            <>
              <button type="button" className="academic-secondary-button" disabled={saving} onClick={publication.close}>
                Keep editing
              </button>
              <button
                type="button"
                className="academic-primary-button"
                disabled={!canPublish || saving}
                onClick={() => void publication.publish()}
              >
                {saving ? 'Publishing…' : 'Publish study plan'}
              </button>
            </>
          }
        >
          <p>Check the subjects in each semester before publishing.</p>
          <ul className="study-plan-review">
            {semesters.map((item) => (
              <li key={item.number}>
                <strong>Semester {item.number}</strong>
                {item.subjects.some((subject) => subject.is_active) ? (
                  <ul>
                    {item.subjects
                      .filter((subject) => subject.is_active)
                      .map((subject) => (
                        <li key={subject.curriculum_subject_id}>
                          {subjectName(subject, state)}{' '}
                          · {subject.is_required ? 'Compulsory' : 'Student choice'}
                        </li>
                      ))}
                  </ul>
                ) : (
                  <p>No subjects included. Check whether this is intended.</p>
                )}
                {choices.data?.groups
                  .filter(
                    (group) =>
                      group.institution_id === state.context.institutionId &&
                      group.curriculum_version_id === version.curriculum_version_id &&
                      group.program_semester_id === item.semester?.program_semester_id,
                  )
                  .map((group) => (
                    <div key={group.choice_group_id}>
                      <strong>{group.name} — choose one option</strong>
                      <ul>
                        {group.options.map((option) => (
                          <li key={option.choice_option_id}>
                            {option.name}:{' '}
                            {option.curriculum_subject_ids
                              .map((id) => {
                                const subject = item.subjects.find((entry) => entry.curriculum_subject_id === id)
                                return subject ? subjectName(subject, state) : 'Subject unavailable'
                              })
                              .join(', ')}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
              </li>
            ))}
          </ul>
          {publication.error && (
            <p className="curriculum-form-error" role="alert">
              {publication.error}
            </p>
          )}
        </CurriculumDrawerFrame>
      )}
    </div>
  )
}
