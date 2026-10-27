import { useEffect, useRef } from 'react'
import type { Department } from '../../../../../types/academicSetup.ts'
import type { SubjectEditor } from '../useSubjectEditor.ts'
import SubjectField from './SubjectField.tsx'

export default function SubjectForm({ editor, departments }: { editor: SubjectEditor; departments?: Department[] }) {
  const ref = useRef<HTMLFormElement>(null)
  useEffect(() => {
    ref.current?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus()
  }, [editor.validationVersion])
  return (
    <form
      id="subject-form"
      ref={ref}
      aria-label={editor.panel === 'edit' ? 'Edit subject' : 'New subject'}
      noValidate
      onSubmit={(event) => {
        event.preventDefault()
        editor.submit()
      }}
    >
      <fieldset disabled={editor.saving || !editor.canManage}>
        <SubjectField
          editor={editor}
          field="name"
          label="Subject Name"
          placeholder="Enter subject name"
          help="e.g. Data Mining"
          required
          maxLength={160}
        />
        <SubjectField
          editor={editor}
          field="code"
          label="Subject Code"
          placeholder="Enter subject code"
          help="e.g. CS501"
          required
          maxLength={32}
        />
        <div className="subject-field">
          <label htmlFor="subject-department">
            Department <span aria-hidden="true">*</span>
          </label>
          <select
            id="subject-department"
            required
            value={editor.draft.department_id}
            disabled={editor.panel === 'edit'}
            aria-invalid={Boolean(editor.errors.department_id)}
            aria-describedby="subject-department-help"
            onChange={(event) => editor.change('department_id', event.target.value)}
          >
            <option value="">Select department</option>
            {departments
              ?.filter((item) => item.is_active || item.department_id === editor.draft.department_id)
              .map((item) => (
                <option key={item.department_id} value={item.department_id}>
                  {item.name}
                </option>
              ))}
            {editor.panel === 'edit' &&
              !departments?.some((item) => item.department_id === editor.draft.department_id) && (
                <option value={editor.draft.department_id}>Unavailable department</option>
              )}
          </select>
          <p
            id="subject-department-help"
            className={editor.errors.department_id ? 'subject-field-error' : 'subject-field-help'}
          >
            {editor.errors.department_id ||
              (editor.panel === 'edit'
                ? 'The department cannot be changed after creation.'
                : 'Choose the department that owns this subject.')}
          </p>
        </div>
        <p className="subject-curriculum-note">
          Semester and subject type are assigned through the program curriculum. A subject can be used in more than one
          curriculum.
        </p>
        <SubjectField
          editor={editor}
          field="credits"
          label="Credits (Optional)"
          placeholder="Enter total credits"
          help="e.g. 4"
          numeric
        />
        <div className="subject-hours">
          <SubjectField editor={editor} field="lecture_hours" label="Lecture Hours (L)" placeholder="3" numeric />
          <SubjectField editor={editor} field="tutorial_hours" label="Tutorial Hours (T)" placeholder="1" numeric />
          <SubjectField editor={editor} field="practical_hours" label="Practical Hours (P)" placeholder="0" numeric />
        </div>
        <SubjectField
          editor={editor}
          field="description"
          label="Subject Description (Optional)"
          placeholder="Enter subject description"
          help="Brief description about the subject"
          maxLength={2000}
        />
        <fieldset className="subject-status-options">
          <legend>
            Status <span aria-hidden="true">*</span>
          </legend>
          {[true, false].map((active) => (
            <label key={String(active)}>
              <input
                type="radio"
                name="subject-status"
                required
                value={String(active)}
                checked={editor.draft.is_active === active}
                onChange={() => editor.change('is_active', active)}
              />
              <span>
                <strong>{active ? 'Active' : 'Inactive'}</strong>
                <small>{active ? 'Subject is active and can be used' : 'Subject is temporarily disabled'}</small>
              </span>
            </label>
          ))}
        </fieldset>
      </fieldset>
    </form>
  )
}
