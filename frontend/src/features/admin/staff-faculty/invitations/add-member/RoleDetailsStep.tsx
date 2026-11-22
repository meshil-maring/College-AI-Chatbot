import type { Department } from '../../../../../types/academicSetup.ts'
import DepartmentFields from './DepartmentFields.tsx'
import { SelectField, TextField } from './FormFields.tsx'
import ResponsibilitiesField from './ResponsibilitiesField.tsx'
import { STAFF_CATEGORIES, employmentTypes } from './memberDraft.ts'
import type { AddMemberDraftModel } from './useAddMemberDraft.ts'

interface Props {
  model: AddMemberDraftModel
  idPrefix: string
  departments: Department[]
}

/** Step 2: departments, employment and the details of the chosen user type. */
export default function RoleDetailsStep({ model, idPrefix, departments }: Props) {
  const field = { model, idPrefix }
  const faculty = model.draft.role === 'faculty'
  const permanent = model.draft.employment_type === 'permanent'
  return (
    <>
      <DepartmentFields model={model} idPrefix={idPrefix} departments={departments} />
      <h3 className="mt-2 text-sm font-semibold text-content">Employment</h3>
      <div className="grid gap-4 sm:grid-cols-2">
        {faculty ? null : (
          <SelectField
            {...field}
            name="staff_category"
            label="Staff category"
            required
            options={STAFF_CATEGORIES}
            placeholder="Choose category…"
          />
        )}
        <SelectField
          {...field}
          name="employment_type"
          label="Employment type"
          required
          options={employmentTypes(model.draft.role)}
          placeholder="Choose type…"
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField {...field} name="employment_start_date" label="Employment start date" type="date" required />
        {permanent ? null : (
          <TextField
            {...field}
            name="contract_end_date"
            label="Contract end date"
            type="date"
            required
            hint="Required for fixed-term employment."
          />
        )}
      </div>
      {faculty ? (
        <>
          <h3 className="mt-2 text-sm font-semibold text-content">Academic background</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField {...field} name="qualification" label="Qualification" maxLength={200} />
            <TextField {...field} name="specialization" label="Specialization" maxLength={200} />
          </div>
          <TextField {...field} name="experience_years" label="Experience (years)" type="number" />
          <p className="text-xs text-muted">
            Responsibilities such as Head of Department are assigned after they join.
          </p>
        </>
      ) : (
        <ResponsibilitiesField model={model} idPrefix={idPrefix} />
      )}
    </>
  )
}
