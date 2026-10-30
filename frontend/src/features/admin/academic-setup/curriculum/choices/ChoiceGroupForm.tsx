import { useEffect, useRef, type FormEvent } from 'react'
import type { AcademicStructureState } from '../../structure/useAcademicStructure.ts'
import type { useChoiceEditor } from './useChoiceEditor.ts'
import { choiceValidation } from './choiceValidation.ts'

interface Props {
  editor: ReturnType<typeof useChoiceEditor>
  structure: AcademicStructureState
  disabled: boolean
  onSubmit: () => Promise<void>
  onManageSubjects: () => void
}
export default function ChoiceGroupForm({ editor, structure, disabled, onSubmit, onManageSubjects }: Props) {
  const { draft, setDraft, editingId, updateOption } = editor
  const records = structure.structure?.records
  const version = records?.curriculum_versions?.find(
    (item) => item.curriculum_version_id === draft.curriculum_version_id,
  )
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
    <form className="registration-panel" onSubmit={submit} aria-label="Subject option group" noValidate>
      <h2>{editingId ? 'Edit option group' : 'Create option group'}</h2>
      <p>Students must choose one complete option. Required subjects are included automatically.</p>
      <fieldset disabled={disabled}>
        <div className="registration-grid">
          <label>
            Curriculum Version
            <select
              required
              disabled={Boolean(editingId)}
              value={draft.curriculum_version_id}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  curriculum_version_id: event.target.value,
                  program_semester_id: '',
                  options: draft.options.map((option) => ({ ...option, curriculum_subject_ids: [] })),
                })
              }
            >
              <option value="">Select a draft curriculum</option>
              {records?.curriculum_versions
                ?.filter((item) => item.status === 'draft' && item.is_active)
                .map((item) => (
                  <option key={item.curriculum_version_id} value={item.curriculum_version_id}>
                    {item.name} · {item.version}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Program Semester
            <select
              required
              disabled={Boolean(editingId)}
              value={draft.program_semester_id}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  program_semester_id: event.target.value,
                  options: draft.options.map((option) => ({ ...option, curriculum_subject_ids: [] })),
                })
              }
            >
              <option value="">Select a semester</option>
              {records?.program_semesters
                ?.filter(
                  (item) =>
                    item.is_active &&
                    item.program_id === version?.program_id &&
                    item.semester_number <= version.total_semesters,
                )
                .sort((left, right) => left.semester_number - right.semester_number)
                .map((item) => (
                  <option key={item.program_semester_id} value={item.program_semester_id}>
                    {item.name}
                  </option>
                ))}
            </select>
          </label>
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
                No subjects are mapped to this curriculum semester yet. Add semester subjects before selecting subjects
                for each option.
              </p>
            ) : !mappings.length ? (
              <p role="status">
                All mapped subjects are marked Required and will be included automatically. Edit the option-specific
                subject mappings and clear Required Subject to make them selectable here.
              </p>
            ) : (
              <p>Choose every subject that belongs to each option below.</p>
            )}
            {required.length > 0 && (
              <p>Common required subjects: {required.map((item) => subjectName(item.course_id)).join(', ')}.</p>
            )}
            <button type="button" className="academic-secondary-button" onClick={onManageSubjects}>
              Manage semester subjects
            </button>
            <p>Your group name and option selections are kept while you manage subjects.</p>
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
            Save option group
          </button>
          {editingId && (
            <button type="button" className="academic-secondary-button" onClick={editor.reset}>
              Cancel editing
            </button>
          )}
        </div>
      </fieldset>
    </form>
  )
}
