import { useEffect, useRef, type FormEvent } from 'react'
import type { AcademicStructureState } from '../../structure/useAcademicStructure.ts'
import type { useChoiceEditor } from './useChoiceEditor.ts'
import { choiceValidation } from './choiceValidation.ts'

interface Props {
  editor: ReturnType<typeof useChoiceEditor>
  structure: AcademicStructureState
  disabled: boolean
  saving: boolean
  onSubmit: () => Promise<void>
  onCancel: () => void
}
export default function ChoiceGroupForm({ editor, structure, disabled, saving, onSubmit, onCancel }: Props) {
  const { draft, setDraft, editingId, updateOption } = editor
  const records = structure.structure?.records
  const semesterMappings =
    records?.curriculum_subjects?.filter(
      (item) =>
        item.is_active &&
        item.curriculum_version_id === draft.curriculum_version_id &&
        item.program_semester_id === draft.program_semester_id,
    ) ?? []
  const mappings = semesterMappings.filter((item) => !item.is_required)
  const required = semesterMappings.filter((item) => item.is_required)
  const subjectName = (courseId: string) =>
    structure.catalogue?.records.courses?.find((course) => course.course_id === courseId)?.name ?? 'Subject unavailable'
  const issues = choiceValidation(draft, new Set(mappings.map((mapping) => mapping.curriculum_subject_id)))
  const validationRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (editor.validationAttempt) validationRef.current?.focus()
  }, [editor.validationAttempt])
  function submit(event: FormEvent) {
    event.preventDefault()
    if (disabled) return
    editor.showValidation()
    if (!issues.length) void onSubmit()
  }
  return (
    <form
      className="registration-panel"
      onSubmit={submit}
      aria-label="Subject choice group"
      noValidate
      aria-busy={saving}
    >
      <h5>{editingId ? 'Edit choice group' : 'Create choice group'}</h5>
      <p>Students choose one complete option from this group. Compulsory subjects are included automatically.</p>
      <fieldset disabled={disabled}>
        <div className="registration-grid">
          <label>
            Group Name
            <input
              required
              maxLength={160}
              value={draft.name}
              placeholder="Semester 3 subject choices"
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            />
          </label>
        </div>
        {draft.program_semester_id && (
          <div className="registration-preparation">
            {!semesterMappings.length ? (
              <p role="status">
                Add subjects to this semester first. Leave Every student must take this subject unchecked for subjects
                students can choose.
              </p>
            ) : !mappings.length ? (
              <p role="status">
                All subjects in this semester are compulsory. Edit a subject above and uncheck Every student must take
                this subject to make it available for choices.
              </p>
            ) : (
              <p>Choose every subject that belongs to each option below.</p>
            )}
            {required.length > 0 && (
              <p>Compulsory subjects: {required.map((item) => subjectName(item.course_id)).join(', ')}.</p>
            )}
            <p>You can add or edit subjects above while keeping this group draft open.</p>
          </div>
        )}
        <div className="registration-grid">
          {draft.options.map((option, index) => (
            <fieldset className="registration-option" key={index}>
              <legend>Option {index + 1} — take all selected subjects</legend>
              <label>
                Option Name
                <input
                  required
                  maxLength={160}
                  value={option.name}
                  onChange={(event) => updateOption(index, { name: event.target.value })}
                />
              </label>
              {mappings.map((mapping) => (
                <label className="registration-check" key={mapping.curriculum_subject_id}>
                  <input
                    type="checkbox"
                    checked={option.curriculum_subject_ids.includes(mapping.curriculum_subject_id)}
                    onChange={(event) =>
                      updateOption(index, {
                        curriculum_subject_ids: event.target.checked
                          ? [...option.curriculum_subject_ids, mapping.curriculum_subject_id]
                          : option.curriculum_subject_ids.filter((id) => id !== mapping.curriculum_subject_id),
                      })
                    }
                  />
                  {subjectName(mapping.course_id)}
                </label>
              ))}
              {draft.options.length > 2 && (
                <button
                  type="button"
                  className="academic-secondary-button"
                  onClick={() => setDraft({ ...draft, options: draft.options.filter((_, item) => item !== index) })}
                >
                  Remove option
                </button>
              )}
            </fieldset>
          ))}
        </div>
        {editor.validationAttempt > 0 && issues.length > 0 && (
          <div ref={validationRef} role="alert" tabIndex={-1} className="academic-request-error">
            <p>Complete these entries before saving:</p>
            <ul>
              {issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="registration-actions">
          <button
            type="button"
            className="academic-secondary-button"
            disabled={draft.options.length >= 20}
            onClick={() =>
              setDraft({
                ...draft,
                options: [...draft.options, { name: `Option ${draft.options.length + 1}`, curriculum_subject_ids: [] }],
              })
            }
          >
            Add option
          </button>
          <button type="submit" className="academic-primary-button">
            {saving ? 'Saving…' : 'Save choice group'}
          </button>
        </div>
      </fieldset>
      <button type="button" className="academic-secondary-button" disabled={saving} onClick={onCancel}>
        Cancel
      </button>
    </form>
  )
}
