import type { ProgramEditor } from '../useProgramEditor.ts'

interface Props {
  editor: ProgramEditor
  field: 'name' | 'code' | 'duration_years' | 'total_credits' | 'description'
  label: string
  placeholder: string
  help?: string
  required?: boolean
  maxLength?: number
  numeric?: boolean
}
export default function ProgramField({ editor, field, label, placeholder, help, required, maxLength, numeric }: Props) {
  const error = editor.errors[field]
  const id = `program-${field}`
  const shared = {
    id,
    name: field,
    required,
    maxLength,
    placeholder,
    value: editor.draft[field],
    'aria-invalid': Boolean(error),
    'aria-describedby': error || help ? `${id}-help` : undefined,
    onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      editor.change(field, event.target.value),
  }
  return (
    <div className="program-field">
      <label htmlFor={id}>
        {label} {required && <span aria-hidden="true">*</span>}
      </label>
      {field === 'description' ? (
        <textarea {...shared} rows={2} />
      ) : (
        <input
          {...shared}
          type={numeric ? 'number' : 'text'}
          step={numeric ? 'any' : undefined}
          min={field === 'duration_years' ? '0' : undefined}
          list={field === 'duration_years' ? 'program-durations' : undefined}
          autoFocus={field === 'name'}
        />
      )}
      {(error || help) && (
        <p id={`${id}-help`} className={error ? 'program-field-error' : 'program-field-help'}>
          {error || help}
        </p>
      )}
    </div>
  )
}
