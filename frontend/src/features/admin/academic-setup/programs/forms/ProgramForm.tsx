import { useEffect, useRef } from 'react'
import type { Department } from '../../../../../types/academicSetup.ts'
import type { ProgramEditor } from '../useProgramEditor.ts'
import ProgramField from './ProgramField.tsx'
import ProgramRelationships from './ProgramRelationships.tsx'

export default function ProgramForm({ editor, departments }: { editor: ProgramEditor; departments?: Department[] }) {
  const ref = useRef<HTMLFormElement>(null)
  useEffect(() => {
    ref.current?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus()
  }, [editor.validationVersion])
  return (
    <form
      id="program-form"
      ref={ref}
      aria-label={editor.panel === 'edit' ? 'Edit degree program' : 'New degree program'}
      noValidate
      onSubmit={(event) => {
        event.preventDefault()
        editor.submit()
      }}
    >
      <fieldset disabled={editor.saving || !editor.canManage}>
        <ProgramField
          editor={editor}
          field="name"
          label="Program Name"
          placeholder="Enter program name"
          help="e.g. B.Tech Computer Science"
          required
          maxLength={160}
        />
        <ProgramField
          editor={editor}
          field="code"
          label="Program Code"
          placeholder="Enter program code"
          help="e.g. CSE (up to 32 characters)"
          required
          maxLength={32}
        />
        <ProgramRelationships editor={editor} departments={departments} />
        <ProgramField
          editor={editor}
          field="total_credits"
          label="Total Credits (Optional)"
          placeholder="Enter total credits"
          help="e.g. 160"
          numeric
        />
        <ProgramField
          editor={editor}
          field="description"
          label="Program Description (Optional)"
          placeholder="Enter program description"
          help="Brief description about the program"
          maxLength={2000}
        />
        <fieldset className="program-status-options">
          <legend>
            Status <span aria-hidden="true">*</span>
          </legend>
          {[true, false].map((active) => (
            <label key={String(active)}>
              <input
                type="radio"
                name="program-status"
                required
                value={String(active)}
                checked={editor.draft.is_active === active}
                onChange={() => editor.change('is_active', active)}
              />
              <span>
                <strong>{active ? 'Active' : 'Inactive'}</strong>
                <small>{active ? 'Program is active and can be used' : 'Program is temporarily disabled'}</small>
              </span>
            </label>
          ))}
        </fieldset>
      </fieldset>
    </form>
  )
}
