import type { SectionEditor } from './useSectionEditor.ts'

export default function SectionRelationships({ editor }: { editor: SectionEditor }) {
  const { draft, change, state } = editor
  const editing = Boolean(editor.panel?.record)
  const batch = state.batches.find((item) => item.id === draft.batchId)
  const program = state.programs.find((item) => item.id === batch?.programId)
  return (
    <>
      <div className="section-field">
        <label htmlFor="section-batch">
          Batch <span aria-hidden="true">*</span>
        </label>
        <select
          id="section-batch"
          required
          value={draft.batchId}
          disabled={editing || editor.saving}
          onChange={(event) => change('batchId', event.target.value)}
          aria-describedby="section-batch-help"
        >
          <option value="">Select batch</option>
          {state.batches
            .filter((item) => item.active || item.id === draft.batchId)
            .map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
        </select>
        <p id="section-batch-help">The batch retains its program and published curriculum assignment.</p>
      </div>
      <div className="section-field">
        <label htmlFor="section-program">Program</label>
        <input id="section-program" disabled value={program?.name ?? ''} placeholder="Auto-filled from batch" />
      </div>
      <div className="section-field">
        <label htmlFor="section-year">Batch Academic Year</label>
        <input id="section-year" disabled value={batch?.academicYear ?? ''} placeholder="Auto-filled from batch" />
      </div>
      <div className="section-field">
        <label htmlFor="section-stage">
          Program Semester <span aria-hidden="true">*</span>
        </label>
        <select
          id="section-stage"
          required
          value={draft.programSemesterId}
          disabled={editing || editor.saving || !batch}
          onChange={(event) => change('programSemesterId', event.target.value)}
        >
          <option value="">Select program semester</option>
          {state.stages
            .filter(
              (stage) =>
                stage.program_id === batch?.programId &&
                stage.semester_number <= (batch?.totalSemesters ?? 0) &&
                (stage.is_active || stage.program_semester_id === draft.programSemesterId),
            )
            .map((stage) => (
              <option key={stage.program_semester_id} value={stage.program_semester_id}>
                {stage.name}
              </option>
            ))}
        </select>
      </div>
      <div className="section-field">
        <label htmlFor="section-term">
          Teaching Term <span aria-hidden="true">*</span>
        </label>
        <select
          id="section-term"
          required
          value={draft.semesterId}
          disabled={editing || editor.saving}
          onChange={(event) => change('semesterId', event.target.value)}
        >
          <option value="">Select teaching term</option>
          {state.terms
            .filter((term) => term.available || term.semester_id === draft.semesterId)
            .map((term) => (
              <option key={term.semester_id} value={term.semester_id}>
                {term.name} (
                {state.years.find((year) => year.academic_year_id === term.academic_year_id)?.name ?? 'Unavailable'})
              </option>
            ))}
        </select>
        <p>A dated teaching period is separate from program progression.</p>
      </div>
    </>
  )
}
