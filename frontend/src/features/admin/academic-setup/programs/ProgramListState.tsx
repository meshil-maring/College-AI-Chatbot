import { Database, GraduationCap, LockKeyhole, Search, TriangleAlert } from 'lucide-react'
import type { ProgramsState } from './usePrograms.ts'

export default function ProgramListState({ state, onCreate }: { state: ProgramsState; onCreate: () => void }) {
  const missing = !state.records
  const Icon = state.denied
    ? LockKeyhole
    : state.error
      ? TriangleAlert
      : missing
        ? Database
        : state.records?.length
          ? Search
          : GraduationCap
  const title = state.denied
    ? 'Program access is unavailable'
    : state.error && missing
      ? 'Programs could not be loaded'
      : missing
        ? 'Program data is not connected'
        : state.records?.length
          ? 'No programs match your filters'
          : 'No programs yet'
  return (
    <div className="program-list-state">
      <span className="program-state-icon">
        <Icon aria-hidden="true" />
      </span>
      <h2>{title}</h2>
      <p>
        {state.denied
          ? 'Your account cannot view these program records. Contact your institution administrator.'
          : state.error && missing
            ? 'We could not retrieve program records. Try again to reload this list.'
            : missing
              ? 'Program records and totals will appear when an authorized data source is available.'
              : state.records?.length
                ? 'Try a different name, code, department, degree type or status, or clear your filters.'
                : 'Create your first program to organize the degrees offered by your departments.'}
      </p>
      {state.error && !state.denied ? (
        <button
          type="button"
          className="academic-secondary-button"
          onClick={() => void state.query.refetch()}
          disabled={state.query.isFetching}
        >
          Retry
        </button>
      ) : !missing && state.records?.length ? (
        <button type="button" className="academic-primary-button" onClick={state.clearFilters}>
          Clear filters
        </button>
      ) : state.canCreate ? (
        <button type="button" className="academic-primary-button" onClick={onCreate} disabled={state.busy}>
          Add Program
        </button>
      ) : null}
    </div>
  )
}
