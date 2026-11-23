import { useId } from 'react'
import type { AcademicCatalogue, AcademicEntity } from '../../../../types/academicSetup.ts'
import { academicParents } from '../academicSetupParents.ts'
import type { AcademicTextField } from '../academicSetupForm.ts'
import { academicInputClass, type AcademicFieldsProps } from './academicFormControls.ts'

export default function AcademicRelationFields({
  entity,
  catalogue,
  draft,
  editing,
  setDraft,
}: AcademicFieldsProps & { entity: AcademicEntity; catalogue: AcademicCatalogue }) {
  const hintId = useId()
  const active = academicParents(catalogue, entity)
  const rows = catalogue.records
  const fields: {
    key: AcademicTextField
    label: string
    optional?: boolean
    options: { id: string; name: string; is_active: boolean }[]
  }[] = []
  if (entity === 'programs' || entity === 'courses')
    fields.push({
      key: 'department_id',
      label: 'Department',
      options: (rows.departments ?? []).map((row) => ({
        id: row.department_id,
        name: `${row.name} (${row.code})`,
        is_active: active.departments.has(row.department_id),
      })),
    })
  if (entity === 'semesters')
    fields.push({
      key: 'academic_year_id',
      label: 'Academic year',
      options: (rows.academic_years ?? []).map((row) => ({
        id: row.academic_year_id,
        name: `${row.name} (${row.code})`,
        is_active: active.years.has(row.academic_year_id),
      })),
    })
  function change(key: AcademicTextField, value: string) {
    setDraft((current) => ({ ...current, [key]: value }))
  }
  return (
    <>
      {fields.map((field) => {
        const options = field.options.filter((row) => row.is_active || (editing && row.id === draft[field.key]))
        return (
          <div key={field.key} className="text-sm text-content">
            <label>
              {field.label}
              {field.optional ? ' (optional)' : ''}
              <select
                required={!field.optional}
                aria-describedby={`${hintId}-${field.key}`}
                disabled={editing}
                value={draft[field.key]}
                onChange={(event) => change(field.key, event.target.value)}
                className={academicInputClass}
              >
                <option value="">{field.optional ? 'All semesters' : `Choose ${field.label.toLowerCase()}`}</option>
                {options.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                    {row.is_active ? '' : ' (inactive)'}
                  </option>
                ))}
                {editing && draft[field.key] && !options.some((row) => row.id === draft[field.key]) && (
                  <option value={draft[field.key]}>Current {field.label.toLowerCase()} (details unavailable)</option>
                )}
              </select>
            </label>
            <span id={`${hintId}-${field.key}`} className="mt-1 block text-xs text-muted">
              Cannot be changed after creation.
            </span>
          </div>
        )
      })}
    </>
  )
}
