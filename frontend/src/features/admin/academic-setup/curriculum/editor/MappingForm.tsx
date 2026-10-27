import { useEffect, useRef } from 'react'
import type { CourseType } from '../../../../../types/academicSetup.ts'
import { COURSE_TYPE_LABELS } from '../../forms/academicCourseTypes.ts'
import type { CurriculumState } from '../useCurriculum.ts'
import type { MappingEditor } from './useMappingEditor.ts'

export default function MappingForm({ state, editor }: { state: CurriculumState; editor: MappingEditor }) {
  const ref = useRef<HTMLFormElement>(null)
  const editing = editor.panel === 'edit'
  const program = state.programs?.find((item) => item.program_id === editor.draft.program_id)
  const courses = state.courses?.filter(
    (item) => state.parents?.courses.has(item.course_id) || (editing && item.course_id === editor.draft.course_id),
  )
  const semesters = state.semesters?.filter(
    (item) =>
      state.parents?.semesters.has(item.semester_id) || (editing && item.semester_id === editor.draft.semester_id),
  )
  useEffect(() => {
    ref.current?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus()
  }, [editor.validationVersion])
  return (
    <form
      id="curriculum-mapping-form"
      ref={ref}
      className="curriculum-form"
      aria-label={editing ? 'Edit subject mapping' : 'New subject mapping'}
      noValidate
      onSubmit={(event) => {
        event.preventDefault()
        editor.submit()
      }}
    >
      <fieldset disabled={editor.saving || !editor.canManage}>
        <div className="curriculum-field">
          <label htmlFor="mapping-program">Program</label>
          <input
            id="mapping-program"
            value={program ? `${program.name} (${program.code})` : 'Unavailable program'}
            disabled
          />
          {editor.errors.program_id && <p className="curriculum-field-error">{editor.errors.program_id}</p>}
        </div>
        <div className="curriculum-field">
          <label htmlFor="mapping-subject">
            Subject <span aria-hidden="true">*</span>
          </label>
          <select
            id="mapping-subject"
            required
            autoFocus
            disabled={editing}
            value={editor.draft.course_id}
            aria-invalid={Boolean(editor.errors.course_id)}
            aria-describedby="mapping-subject-help"
            onChange={(event) => editor.change('course_id', event.target.value)}
          >
            <option value="">Select subject</option>
            {courses?.map((course) => (
              <option key={course.course_id} value={course.course_id}>
                {course.name} ({course.code})
              </option>
            ))}
            {editing && !courses?.some((course) => course.course_id === editor.draft.course_id) && (
              <option value={editor.draft.course_id}>Unavailable subject</option>
            )}
          </select>
          <p
            id="mapping-subject-help"
            className={editor.errors.course_id ? 'curriculum-field-error' : 'curriculum-field-help'}
          >
            {editor.errors.course_id ||
              (editing
                ? 'The subject cannot be changed after creation.'
                : 'Choose an active subject from the institution catalogue.')}
          </p>
        </div>
        <div className="curriculum-field">
          <label htmlFor="mapping-semester">Academic Term (Optional)</label>
          <select
            id="mapping-semester"
            disabled={editing}
            value={editor.draft.semester_id}
            aria-invalid={Boolean(editor.errors.semester_id)}
            aria-describedby="mapping-semester-help"
            onChange={(event) => editor.change('semester_id', event.target.value)}
          >
            <option value="">All semesters</option>
            {semesters?.map((semester) => (
              <option key={semester.semester_id} value={semester.semester_id}>
                {semester.name} ({semester.code}) · Semester {semester.semester_number}
              </option>
            ))}
            {editing &&
              editor.draft.semester_id &&
              !semesters?.some((semester) => semester.semester_id === editor.draft.semester_id) && (
                <option value={editor.draft.semester_id}>Unavailable academic term</option>
              )}
          </select>
          <p
            id="mapping-semester-help"
            className={editor.errors.semester_id ? 'curriculum-field-error' : 'curriculum-field-help'}
          >
            {editor.errors.semester_id ||
              (editing
                ? 'The academic term cannot be changed after creation.'
                : 'These are dated academic terms; blank applies to all semesters.')}
          </p>
        </div>
        <div className="curriculum-field">
          <label htmlFor="mapping-type">
            Subject Type <span aria-hidden="true">*</span>
          </label>
          <select
            id="mapping-type"
            required
            value={editor.draft.course_type}
            aria-invalid={Boolean(editor.errors.course_type)}
            onChange={(event) => editor.change('course_type', event.target.value as CourseType)}
          >
            {Object.entries(COURSE_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          {editor.errors.course_type && <p className="curriculum-field-error">{editor.errors.course_type}</p>}
        </div>
        <label className="curriculum-checkbox">
          <input
            type="checkbox"
            checked={editor.draft.is_required}
            onChange={(event) => editor.change('is_required', event.target.checked)}
          />
          Required subject
        </label>
        <fieldset className="curriculum-status-options">
          <legend>
            Mapping Status <span aria-hidden="true">*</span>
          </legend>
          {[true, false].map((active) => (
            <label key={String(active)}>
              <input
                type="radio"
                name="mapping-status"
                checked={editor.draft.is_active === active}
                onChange={() => editor.change('is_active', active)}
              />
              <span>
                <strong>{active ? 'Active' : 'Inactive'}</strong>
                <small>{active ? 'Mapping is active and can be used' : 'Mapping is temporarily disabled'}</small>
              </span>
            </label>
          ))}
        </fieldset>
      </fieldset>
    </form>
  )
}
