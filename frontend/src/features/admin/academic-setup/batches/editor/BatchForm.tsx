import { batchStatuses } from '../batchModel.ts'
import type { BatchEditor } from './useBatchEditor.ts'
import BatchRelationships from './BatchRelationships.tsx'

export default function BatchForm({ editor }: { editor: BatchEditor }) {
  const { draft, change } = editor
  return (
    <form
      id="batch-form"
      className="batch-form"
      aria-label="Batch details"
      onSubmit={(event) => {
        event.preventDefault()
        editor.submit()
      }}
    >
      <div className="batch-field">
        <label htmlFor="batch-name">
          Batch Name <span aria-hidden="true">*</span>
        </label>
        <input
          id="batch-name"
          required
          maxLength={160}
          placeholder="Enter batch name"
          value={draft.name}
          onChange={(event) => change('name', event.target.value)}
          aria-describedby="batch-name-help"
        />
        <p id="batch-name-help">e.g. CSE 2026</p>
      </div>
      <div className="batch-field">
        <label htmlFor="batch-code">
          Batch Code <span aria-hidden="true">*</span>
        </label>
        <input
          id="batch-code"
          required
          maxLength={32}
          placeholder="Enter batch code"
          value={draft.code}
          onChange={(event) => change('code', event.target.value)}
          aria-describedby="batch-code-help"
        />
        <p id="batch-code-help">e.g. CSE26</p>
      </div>
      <BatchRelationships editor={editor} />
      <div className="batch-year-fields">
        <div className="batch-field">
          <label htmlFor="batch-start">
            Start Year <span aria-hidden="true">*</span>
          </label>
          <input
            id="batch-start"
            disabled={Boolean(editor.panel?.record) || editor.saving}
            type="number"
            min={1900}
            max={2199}
            step={1}
            required
            value={draft.startYear}
            onChange={(event) => change('startYear', event.target.value)}
          />
        </div>
        <div className="batch-field">
          <label htmlFor="batch-end">
            End Year <span aria-hidden="true">*</span>
          </label>
          <input
            id="batch-end"
            disabled={Boolean(editor.panel?.record) || editor.saving}
            type="number"
            min={1901}
            max={2200}
            step={1}
            required
            value={draft.endYear}
            onChange={(event) => change('endYear', event.target.value)}
          />
        </div>
      </div>
      <div className="batch-field">
        <label htmlFor="batch-count">Expected Student Count (Optional)</label>
        <input
          id="batch-count"
          type="number"
          min={0}
          step={1}
          placeholder="Enter expected count"
          value={draft.expectedCount}
          onChange={(event) => change('expectedCount', event.target.value)}
          aria-describedby="batch-count-help"
        />
        <p id="batch-count-help">e.g. 120</p>
      </div>
      <div className="batch-field">
        <label htmlFor="batch-description">Description (Optional)</label>
        <textarea
          id="batch-description"
          rows={3}
          maxLength={2000}
          placeholder="Enter batch description"
          value={draft.description}
          onChange={(event) => change('description', event.target.value)}
          aria-describedby="batch-description-help"
        />
        <p id="batch-description-help">Brief description about this batch</p>
      </div>
      <fieldset className="batch-status-options">
        <legend>
          Status <span aria-hidden="true">*</span>
        </legend>
        {batchStatuses.map((item) => (
          <label key={item.value}>
            <input
              type="radio"
              name="batch-status"
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
