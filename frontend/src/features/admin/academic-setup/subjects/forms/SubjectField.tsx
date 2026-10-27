import type { SubjectEditor } from '../useSubjectEditor.ts'

interface Props {
  editor: SubjectEditor
  field: 'name' | 'code' | 'credits' | 'lecture_hours' | 'tutorial_hours' | 'practical_hours' | 'description'
  label: string
  placeholder: string
  help?: string
  required?: boolean
  maxLength?: number
  numeric?: boolean
}
export default function SubjectField({ editor, field, label, placeholder, help, required, maxLength, numeric }: Props) {
  const error = editor.errors[field]
  const id = `subject-${field}`
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
    <div className="subject-field">
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
          min={numeric ? '0' : undefined}
          autoFocus={field === 'name'}
        />
      )}
      {(error || help) && (
        <p id={`${id}-help`} className={error ? 'subject-field-error' : 'subject-field-help'}>
          {error || help}
        </p>
      )}
    </div>
  )
}
