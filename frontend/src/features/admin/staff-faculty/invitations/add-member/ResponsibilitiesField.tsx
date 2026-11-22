import type { DraftFieldsModel } from './memberDraft.ts'
import { X } from 'lucide-react'
import { useState, type KeyboardEvent } from 'react'
import { BUTTON_CLASS } from '../../StaffFacultyUI.tsx'
import { FieldError, INPUT_CLASS } from './FormFields.tsx'

const SUGGESTIONS = ['Admissions desk', 'Fee collection', 'Records management', 'Student support']
const MAX = 20

/** Institution-defined job responsibilities for a Staff member (at least one). */
export default function ResponsibilitiesField({ model, idPrefix }: { model: DraftFieldsModel; idPrefix: string }) {
  const [text, setText] = useState('')
  const items = model.draft.responsibilities
  const inputId = `${idPrefix}-responsibility`
  const invalid = Boolean(model.errors.responsibilities)

  function add(value: string) {
    const item = value.split(/\s+/).filter(Boolean).join(' ').slice(0, 80)
    if (!item || items.length >= MAX) return
    if (!items.some((existing) => existing.toLowerCase() === item.toLowerCase())) {
      model.update('responsibilities', [...items, item])
    }
    setText('')
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') {
      event.preventDefault()
      add(text)
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={inputId} className="text-sm font-medium text-content">
        Responsibilities <span aria-hidden="true">*</span>
      </label>
      <div className="flex gap-2">
        <input
          id={inputId}
          value={text}
          maxLength={80}
          autoComplete="off"
          placeholder="Type a responsibility and press Enter"
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
          className={INPUT_CLASS}
          aria-invalid={invalid}
          aria-describedby={invalid ? `${idPrefix}-responsibilities-error` : undefined}
        />
        <button type="button" onClick={() => add(text)} disabled={!text.trim()} className={BUTTON_CLASS}>
          Add
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.filter((item) => !items.includes(item)).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => add(item)}
            className="rounded-full border border-dashed border-line px-3 py-1 text-xs text-muted hover:bg-hover"
          >
            + {item}
          </button>
        ))}
      </div>
      {items.length ? (
        <ul aria-label="Chosen responsibilities" className="flex flex-wrap gap-2">
          {items.map((item) => (
            <li key={item} className="flex items-center gap-1 rounded-full bg-hover py-1 pl-3 pr-1 text-sm">
              {item}
              <button
                type="button"
                aria-label={`Remove ${item}`}
                onClick={() =>
                  model.update(
                    'responsibilities',
                    items.filter((existing) => existing !== item),
                  )
                }
                className="inline-flex size-6 items-center justify-center rounded-full hover:bg-surface"
              >
                <X aria-hidden="true" className="size-3.5" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <FieldError model={model} idPrefix={idPrefix} name="responsibilities" />
    </div>
  )
}
