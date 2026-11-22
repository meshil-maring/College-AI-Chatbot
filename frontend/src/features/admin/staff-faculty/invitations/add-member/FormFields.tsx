import { SELECT_CLASS } from '../../StaffFacultyUI.tsx'
import type { DraftField, MemberDraft, DraftFieldsModel } from './memberDraft.ts'

type StringField = { [K in DraftField]: MemberDraft[K] extends string ? K : never }[DraftField]

interface FieldProps {
  model: DraftFieldsModel
  /** Prefix for element ids so errors are announced with their field. */
  idPrefix: string
  name: StringField
  label: string
  required?: boolean
  hint?: string
}

export const LABEL_CLASS = 'flex flex-col gap-1 text-sm font-medium text-content'
export const INPUT_CLASS = `${SELECT_CLASS} w-full aria-[invalid=true]:border-danger`

function a11y({ model, idPrefix, name }: FieldProps) {
  return model.errors[name]
    ? { 'aria-invalid': true as const, 'aria-describedby': `${idPrefix}-${name}-error` }
    : { 'aria-invalid': false as const }
}

export function FieldError({ model, idPrefix, name }: Pick<FieldProps, 'model' | 'idPrefix'> & { name: DraftField }) {
  const message = model.errors[name]
  return message ? (
    <span id={`${idPrefix}-${name}-error`} className="text-xs text-danger">
      {message}
    </span>
  ) : null
}

function Label({ label, required, hint }: Pick<FieldProps, 'label' | 'required' | 'hint'>) {
  return (
    <span className="flex flex-col">
      <span>
        {label}{' '}
        {required ? <span aria-hidden="true">*</span> : <span className="font-normal text-muted">(optional)</span>}
      </span>
      {hint ? <span className="text-xs font-normal text-muted">{hint}</span> : null}
    </span>
  )
}

export function TextField(
  props: FieldProps & { type?: 'text' | 'email' | 'tel' | 'date' | 'number'; maxLength?: number },
) {
  const { model, name, type = 'text', maxLength } = props
  return (
    <label className={LABEL_CLASS}>
      <Label {...props} />
      <input
        type={type}
        value={model.draft[name]}
        autoComplete="off"
        maxLength={maxLength}
        {...(type === 'number' ? { min: 0, max: 70, step: 0.5, inputMode: 'decimal' as const } : {})}
        onChange={(event) => model.update(name, event.target.value)}
        className={INPUT_CLASS}
        {...a11y(props)}
      />
      <FieldError {...props} />
    </label>
  )
}

export function SelectField(props: FieldProps & { options: Record<string, string>; placeholder: string }) {
  const { model, name, options, placeholder } = props
  return (
    <label className={LABEL_CLASS}>
      <Label {...props} />
      <select
        value={model.draft[name]}
        onChange={(event) => model.update(name, event.target.value)}
        className={INPUT_CLASS}
        {...a11y(props)}
      >
        <option value="">{placeholder}</option>
        {Object.entries(options).map(([value, text]) => (
          <option key={value} value={value}>
            {text}
          </option>
        ))}
      </select>
      <FieldError {...props} />
    </label>
  )
}
