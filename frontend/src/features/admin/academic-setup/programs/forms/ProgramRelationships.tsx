import type { Department } from '../../../../../types/academicSetup.ts'
import type { ProgramEditor } from '../useProgramEditor.ts'
import { DEGREE_TYPES } from '../programModel.ts'
import ProgramField from './ProgramField.tsx'

export default function ProgramRelationships({
  editor,
  departments,
}: {
  editor: ProgramEditor
  departments?: Department[]
}) {
  const editing = editor.panel === 'edit'
  const { draft, errors } = editor
  const choices =
    departments?.filter((item) => item.is_active || (editing && item.department_id === draft.department_id)) ?? []
  const types = [...new Set([...DEGREE_TYPES, ...(draft.degree_type ? [draft.degree_type] : [])])]
  return (
    <>
      <div className="program-field">
        <label htmlFor="program-department">
          Department <span aria-hidden="true">*</span>
        </label>
        <select
          id="program-department"
          required
          value={draft.department_id}
          disabled={editing}
          onChange={(event) => editor.change('department_id', event.target.value)}
          aria-invalid={Boolean(errors.department_id)}
          aria-describedby={errors.department_id || editing ? 'program-department-help' : undefined}
        >
          <option value="">Select department</option>
          {editing && !choices.some((item) => item.department_id === draft.department_id) && (
            <option value={draft.department_id}>Current department (details unavailable)</option>
          )}
          {choices.map((item) => (
            <option value={item.department_id} key={item.department_id}>
              {item.name}
              {item.is_active ? '' : ' (Inactive)'}
            </option>
          ))}
        </select>
        {(errors.department_id || editing) && (
          <p
            id="program-department-help"
            className={errors.department_id ? 'program-field-error' : 'program-field-help'}
          >
            {errors.department_id || 'The department cannot be changed after creation.'}
          </p>
        )}
      </div>
      <div className="program-field">
        <label htmlFor="program-degree">
          Degree Type <span aria-hidden="true">*</span>
        </label>
        <select
          id="program-degree"
          required
          value={draft.degree_type}
          onChange={(event) => editor.change('degree_type', event.target.value)}
          aria-invalid={Boolean(errors.degree_type)}
          aria-describedby={errors.degree_type ? 'program-degree-error' : undefined}
        >
          <option value="">Select degree type</option>
          {types.map((type) => (
            <option key={type}>{type}</option>
          ))}
        </select>
        {errors.degree_type && (
          <p id="program-degree-error" className="program-field-error">
            {errors.degree_type}
          </p>
        )}
      </div>
      <ProgramField
        editor={editor}
        field="duration_years"
        label="Duration (Years)"
        placeholder="Select duration"
        required
        numeric
      />
      <datalist id="program-durations">
        {[1, 2, 3, 4, 5, 6].map((value) => (
          <option value={value} key={value} />
        ))}
      </datalist>
    </>
  )
}
