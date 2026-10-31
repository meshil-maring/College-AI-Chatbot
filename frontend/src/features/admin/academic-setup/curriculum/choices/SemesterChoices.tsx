import { useEffect, useRef } from 'react'
import type { CurriculumVersion, ProgramSemester } from '../../../../../types/academicStructure.ts'
import type { AcademicStructureState } from '../../structure/useAcademicStructure.ts'
import type { RegistrationAdminState } from '../../registration/useRegistrationAdmin.ts'
import ChoiceGroupForm from './ChoiceGroupForm.tsx'
import { useSemesterChoices } from './useSemesterChoices.ts'
import '../../registration/registration.css'
import './semester-choices.css'

export default function SemesterChoices({
  structure,
  state,
  version,
  semester,
  onDraftChange,
}: {
  structure: AcademicStructureState
  state: RegistrationAdminState
  version: CurriculumVersion
  semester: ProgramSemester
  onDraftChange: (id: string, open: boolean) => void
}) {
  const choices = useSemesterChoices(structure, state, version, semester)
  const ref = useRef<HTMLElement>(null)
  const wasOpen = useRef(false)
  const draftKey = `${version.curriculum_version_id}:${semester.program_semester_id}`
  useEffect(() => {
    onDraftChange(draftKey, choices.open)
    return () => onDraftChange(draftKey, false)
  }, [choices.open, draftKey, onDraftChange])
  useEffect(() => {
    if (choices.open) ref.current?.querySelector<HTMLInputElement>('form input')?.focus()
    else if (wasOpen.current) ref.current?.querySelector<HTMLButtonElement>('header button')?.focus()
    wasOpen.current = choices.open
  }, [choices.open])
  return (
    <section
      ref={ref}
      className="semester-choices"
      aria-label={`Student choices in Semester ${semester.semester_number}`}
    >
      <header>
        <h4>Student choices</h4>
        {version.status === 'draft' && state.data?.can_manage_choices && (
          <button
            type="button"
            className="academic-secondary-button"
            disabled={!choices.canWrite}
            onClick={choices.add}
          >
            Add choice group
          </button>
        )}
      </header>
      {!state.data ? (
        <p>Student choices are unavailable until they finish loading successfully.</p>
      ) : (
        <>
          {!choices.groups.length && (
            <p>No choice groups. If every subject is compulsory, you can skip this section.</p>
          )}
          {version.status === 'draft' && !state.data.can_manage_choices && <p>Read-only access to student choices.</p>}
          {choices.groups.map((group) => (
            <article className="semester-choice-group" key={group.choice_group_id}>
              <h5>{group.name}</h5>
              <p>Choose one option. Take every subject in that option.</p>
              <div className="registration-grid">
                {group.options.map((option) => (
                  <div className="semester-choice-option" key={option.choice_option_id}>
                    <h6>{option.name}</h6>
                    <ul>
                      {option.curriculum_subject_ids.map((id) => {
                        const mapping = structure.structure?.records.curriculum_subjects?.find(
                          (item) =>
                            item.curriculum_subject_id === id &&
                            item.curriculum_version_id === version.curriculum_version_id &&
                            item.program_semester_id === semester.program_semester_id,
                        )
                        const subject = structure.catalogue?.records.courses?.find(
                          (item) => item.course_id === mapping?.course_id,
                        )
                        return <li key={id}>{subject?.name ?? 'Subject unavailable'}</li>
                      })}
                    </ul>
                  </div>
                ))}
              </div>
              {version.status === 'draft' && state.data?.can_manage_choices && (
                <div className="registration-actions">
                  <button
                    type="button"
                    className="academic-secondary-button"
                    disabled={!choices.canWrite}
                    onClick={() => choices.edit(group)}
                  >
                    Edit {group.name}
                  </button>
                  <button
                    type="button"
                    className="academic-secondary-button"
                    disabled={!choices.canWrite}
                    onClick={() => choices.requestDelete(group.choice_group_id)}
                  >
                    Delete {group.name}
                  </button>
                </div>
              )}
              {choices.deleteId === group.choice_group_id && (
                <div role="group" aria-label={`Confirm deletion of ${group.name}`}>
                  <p>Delete this draft choice group?</p>
                  <div className="registration-actions">
                    <button
                      type="button"
                      className="academic-secondary-button"
                      disabled={!choices.canWrite}
                      onClick={() => void choices.remove()}
                    >
                      Confirm delete
                    </button>
                    <button
                      type="button"
                      className="academic-secondary-button"
                      disabled={state.saving}
                      onClick={() => choices.requestDelete(undefined)}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </article>
          ))}
        </>
      )}
      {choices.open && (
        <ChoiceGroupForm
          editor={choices.editor}
          structure={structure}
          disabled={!choices.canWrite}
          saving={state.saving}
          onSubmit={choices.save}
          onCancel={choices.close}
        />
      )}
    </section>
  )
}
