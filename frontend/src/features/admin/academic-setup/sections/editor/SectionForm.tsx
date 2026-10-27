import { sectionStatuses } from '../sectionModel.ts'
import SectionRelationships from './SectionRelationships.tsx'
import type { SectionEditor } from './useSectionEditor.ts'

export default function SectionForm({ editor }: { editor: SectionEditor }) {
  const { draft, change } = editor
  return (
    <form
      id="section-form"
      className="section-form"
      aria-label="Section details"
      onSubmit={(event) => {
        event.preventDefault()
        editor.submit()
      }}
    >
      <div className="section-field">
        <label htmlFor="section-name">
          Section Name <span aria-hidden="true">*</span>
        </label>
        <input
          id="section-name"
          required
          maxLength={160}
          placeholder="Enter section name"
          value={draft.name}
          onChange={(event) => change('name', event.target.value)}
          aria-describedby="section-name-help"
        />
        <p id="section-name-help">e.g. Section A</p>
      </div>
      <div className="section-field">
        <label htmlFor="section-code">
          Section Code <span aria-hidden="true">*</span>
        </label>
        <input
          id="section-code"
          disabled={Boolean(editor.panel?.record) || editor.saving}
          required
          maxLength={32}
          placeholder="Enter section code"
          value={draft.code}
          onChange={(event) => change('code', event.target.value)}
          aria-describedby="section-code-help"
        />
        <p id="section-code-help">e.g. CSE26A</p>
      </div>
      <SectionRelationships editor={editor} />
      <div className="section-field">
        <label htmlFor="section-capacity">Maximum Capacity (Optional)</label>
        <input
          id="section-capacity"
          type="number"
          min={0}
          step={1}
          placeholder="Enter maximum capacity"
          value={draft.capacity}
          onChange={(event) => change('capacity', event.target.value)}
          aria-describedby="section-capacity-help"
        />
        <p id="section-capacity-help">e.g. 60</p>
      </div>
      <div className="section-field">
        <label htmlFor="section-description">Description (Optional)</label>
        <textarea
          id="section-description"
          rows={3}
          maxLength={2000}
          placeholder="Enter section description"
          value={draft.description}
          onChange={(event) => change('description', event.target.value)}
          aria-describedby="section-description-help"
        />
        <p id="section-description-help">Brief description about this section</p>
      </div>
      <fieldset className="section-status-options">
        <legend>
          Status <span aria-hidden="true">*</span>
        </legend>
        {sectionStatuses.map((item) => (
          <label key={item.value}>
            <input
              type="radio"
              name="section-status"
              value={item.value}
              checked={draft.status === item.value}
              onChange={() => change('status', item.value)}
            />
            <span>
              <strong>{item.label}</strong>
              <small>{item.description}</small>
            </span>
          </label>
        ))}
      </fieldset>
    </form>
  )
}
