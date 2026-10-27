import type { BatchEditor } from './useBatchEditor.ts'

export default function BatchRelationships({ editor }: { editor: BatchEditor }) {
  const { draft, change, state } = editor
  const editing = Boolean(editor.panel?.record)
  return (
    <>
      <div className="batch-field">
        <label htmlFor="batch-program">
          Program <span aria-hidden="true">*</span>
        </label>
        <select
          id="batch-program"
          required
          disabled={editing || editor.saving}
          value={draft.programId}
          onChange={(event) => change('programId', event.target.value)}
        >
          <option value="">Select program</option>
          {state.programs
            .filter((item) => item.active || item.id === draft.programId)
            .map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
        </select>
      </div>
      <div className="batch-field">
        <label htmlFor="batch-curriculum">
          Curriculum Version <span aria-hidden="true">*</span>
        </label>
        <select
          id="batch-curriculum"
          required
          disabled={editing || editor.saving || !draft.programId}
          value={draft.curriculumId}
          aria-describedby="batch-curriculum-help"
          onChange={(event) => change('curriculumId', event.target.value)}
        >
          <option value="">Select curriculum version</option>
          {state.curricula
            .filter((item) => item.programId === draft.programId && (item.active || item.id === draft.curriculumId))
            .map((item) => (
              <option key={item.id} value={item.id}>
                {item.version} (Published)
              </option>
            ))}
        </select>
        <p id="batch-curriculum-help">The assigned published curriculum is retained for the life of this batch.</p>
      </div>
      <div className="batch-field">
        <label htmlFor="batch-year">
          Academic Year <span aria-hidden="true">*</span>
        </label>
        <select
          id="batch-year"
          required
          disabled={editing || editor.saving}
          value={draft.academicYear}
          onChange={(event) => change('academicYear', event.target.value)}
        >
          <option value="">Select academic year</option>
          {state.years
            .filter((year) => year.is_active || year.academic_year_id === draft.academicYear)
            .map((year) => (
              <option key={year.academic_year_id} value={year.academic_year_id}>
                {year.name}
              </option>
            ))}
        </select>
      </div>
    </>
  )
}
