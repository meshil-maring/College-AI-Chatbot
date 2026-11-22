import type { Department } from '../../../../../types/academicSetup.ts'
import { FieldError, INPUT_CLASS, LABEL_CLASS } from './FormFields.tsx'
import type { AddMemberDraftModel } from './useAddMemberDraft.ts'

interface Props {
  model: AddMemberDraftModel
  idPrefix: string
  departments: Department[]
}

/**
 * Primary department plus optional additional departments. Association does not
 * grant teaching access; teaching assignments are configured separately.
 */
export default function DepartmentFields({ model, idPrefix, departments }: Props) {
  const { draft } = model
  const others = departments.filter((department) => department.department_id !== draft.department_id)
  const invalid = Boolean(model.errors.department_id)

  function toggle(id: string, checked: boolean) {
    const chosen = draft.additional_department_ids.filter((item) => item !== id)
    model.update('additional_department_ids', checked ? [...chosen, id] : chosen)
  }

  return (
    <>
      <label className={LABEL_CLASS}>
        <span>
          Primary department <span aria-hidden="true">*</span>
        </span>
        <select
          value={draft.department_id}
          disabled={departments.length === 0}
          onChange={(event) => model.update('department_id', event.target.value)}
          className={INPUT_CLASS}
          aria-invalid={invalid}
          aria-describedby={invalid ? `${idPrefix}-department_id-error` : undefined}
        >
          <option value="">Choose department…</option>
          {departments.map((department) => (
            <option key={department.department_id} value={department.department_id}>
              {department.name} ({department.code})
            </option>
          ))}
        </select>
        {departments.length === 0 ? (
          <span className="text-xs text-warning">Add an active department in Academic Setup first.</span>
        ) : null}
        <FieldError model={model} idPrefix={idPrefix} name="department_id" />
      </label>
      {draft.department_id && others.length > 0 ? (
        <fieldset className="flex flex-col gap-2">
          <legend className="text-sm font-medium text-content">
            Additional departments <span className="font-normal text-muted">(optional)</span>
          </legend>
          <p className="text-xs text-muted">
            Associates them with more departments. Teaching assignments are set separately.
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {others.map((department) => (
              <label key={department.department_id} className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={draft.additional_department_ids.includes(department.department_id)}
                  disabled={
                    !draft.additional_department_ids.includes(department.department_id) &&
                    draft.additional_department_ids.length >= 10
                  }
                  onChange={(event) => toggle(department.department_id, event.target.checked)}
                  className="size-4 accent-[var(--ui-accent)]"
                />
                <span>{department.name}</span>
              </label>
            ))}
          </div>
        </fieldset>
      ) : null}
    </>
  )
}
