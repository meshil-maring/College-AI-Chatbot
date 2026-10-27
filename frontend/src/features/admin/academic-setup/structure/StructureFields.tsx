import type { StructureDraft, StructureField } from './structureFields.ts'

export default function StructureFields({
  fields,
  draft,
  editing,
  saving,
  change,
}: {
  fields: StructureField[]
  draft: StructureDraft
  editing: boolean
  saving: boolean
  change: (field: string, value: string | boolean) => void
}) {
  return (
    <>
      {fields
        .filter((field) => editing || field.key !== 'status')
        .map((field) => {
          const id = `structure-${field.key}`
          const disabled = saving || (editing && Boolean(field.immutable || field.frozen))
          const value = String(draft[field.key] ?? '')
          return (
            <div className="structure-field" key={field.key}>
              <label htmlFor={id}>
                {field.label}
                {field.required && <span aria-hidden="true"> *</span>}
              </label>
              {field.type === 'select' ? (
                <select
                  id={id}
                  required={field.required}
                  disabled={disabled}
                  value={value}
                  onChange={(event) => change(field.key, event.target.value)}
                >
                  <option value="">Select {field.label.toLowerCase()}</option>
                  {disabled && value && !field.options?.some((item) => item.value === value) && (
                    <option value={value}>Current assignment retained</option>
                  )}
                  {field.options?.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : field.type === 'textarea' ? (
                <textarea
                  id={id}
                  rows={3}
                  maxLength={2000}
                  disabled={disabled}
                  value={value}
                  onChange={(event) => change(field.key, event.target.value)}
                />
              ) : field.type === 'checkbox' ? (
                <input
                  id={id}
                  type="checkbox"
                  disabled={disabled}
                  checked={Boolean(draft[field.key])}
                  onChange={(event) => change(field.key, event.target.checked)}
                />
              ) : (
                <input
                  id={id}
                  type={field.type === 'number' ? 'number' : 'text'}
                  required={field.required}
                  disabled={disabled}
                  min={field.min}
                  max={field.max}
                  step={field.type === 'number' ? 1 : undefined}
                  maxLength={['code', 'version'].includes(field.key) ? 32 : 160}
                  value={value}
                  onChange={(event) => change(field.key, event.target.value)}
                />
              )}
              {field.help && <p>{field.help}</p>}
            </div>
          )
        })}
    </>
  )
}
