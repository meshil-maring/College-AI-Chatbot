import { X } from 'lucide-react'
import { useWorkspaceDialog } from '../../../workspace/useWorkspaceDialog.ts'
import type { StructureContext } from '../structure/useAcademicStructure.ts'
import { useRollover } from './useRollover.ts'
import RolloverPreview from './RolloverPreview.tsx'
import './rollover.css'

/** Copies a year's calendar forward and continues each active batch into its next semesters. */
export default function RolloverDialog({ context, onClose }: { context: StructureContext; onClose: () => void }) {
  const state = useRollover(context)
  const ref = useWorkspaceDialog('.calendar-page h1')
  const percent = state.progress?.total ? Math.round((state.progress.done / state.progress.total) * 100) : 0
  const finished = Boolean(state.progress && !state.running && !state.error && !state.hasWork)
  return (
    <dialog
      ref={ref}
      tabIndex={-1}
      className="calendar-drawer rollover-drawer"
      aria-modal="true"
      aria-labelledby="rollover-title"
      aria-describedby="rollover-description"
      aria-busy={state.running}
      onCancel={(event) => {
        event.preventDefault()
        if (!state.running) onClose()
      }}
    >
      <header>
        <div>
          <h2 id="rollover-title">Roll over to next year</h2>
          <p id="rollover-description">
            Create next year's calendar and continue each active batch into its next semesters. Nothing is created until
            you confirm, and records that already exist are reused.
          </p>
        </div>
        <button type="button" aria-label="Close roll-over" disabled={state.running} onClick={onClose}>
          <X aria-hidden="true" />
        </button>
      </header>
      <div className="calendar-drawer-body rollover-body">
        <label className="rollover-source">
          <span>Copy from academic year</span>
          <select
            value={state.sourceId}
            disabled={state.running || !state.years.length}
            onChange={(event) => state.setSourceId(event.target.value)}
          >
            {state.years.map((year) => (
              <option key={year.academic_year_id} value={year.academic_year_id}>
                {year.name}
                {year.is_current ? ' (current)' : ''}
              </option>
            ))}
          </select>
        </label>
        {state.loading && <p role="status">Loading academic records…</p>}
        {!state.loading && !state.years.length && (
          <p className="rollover-empty">Add an academic year with terms before rolling over.</p>
        )}
        {!state.canRun && !state.loading && (
          <p className="rollover-note" role="status">
            Rolling over needs permission to manage academic years, terms, program semesters and sections.
          </p>
        )}
        {state.error && (
          <p className="rollover-error" role="alert">
            Stopped at {state.error} Everything created so far is kept; Retry continues with what is missing.
          </p>
        )}
        {state.progress && (state.running || state.error) && (
          <div className="rollover-progress" role="status">
            <span>
              {state.running ? `Creating ${state.progress.current}…` : 'Stopped'} ({state.progress.done} of{' '}
              {state.progress.total})
            </span>
            <span className="rollover-meter" aria-hidden="true">
              <span style={{ width: `${percent}%` }} />
            </span>
          </div>
        )}
        {finished && (
          <p className="rollover-done" role="status">
            Next year is ready. Review the new sections in Academic Sections.
          </p>
        )}
        {state.plan && <RolloverPreview plan={state.plan} />}
      </div>
      <footer>
        <button type="button" className="academic-secondary-button" disabled={state.running} onClick={onClose}>
          {finished ? 'Done' : 'Cancel'}
        </button>
        <button
          type="button"
          className="academic-primary-button"
          disabled={state.running || !state.canRun || !state.hasWork}
          onClick={() => void state.run()}
        >
          {state.running ? 'Rolling over…' : state.error ? 'Retry' : state.hasWork ? 'Roll over' : 'Nothing to create'}
        </button>
      </footer>
    </dialog>
  )
}
