import { Database, GraduationCap, LockKeyhole, Search, TriangleAlert } from 'lucide-react'
import type { SubjectsState } from './useSubjects.ts'

export default function SubjectListState({ state, onCreate }: { state: SubjectsState; onCreate: () => void }) {
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
    ? 'Subject access is unavailable'
    : state.error && missing
      ? 'Subjects could not be loaded'
      : missing
        ? 'Subject data is not connected'
        : state.records?.length
          ? 'No subjects match your filters'
          : 'No subjects yet'
  return (
    <div className="subject-list-state">
      <span className="subject-state-icon">
        <Icon aria-hidden="true" />
      </span>
      <h2>{title}</h2>
      <p>
        {state.denied
          ? 'Your account cannot view these subject records. Contact your institution administrator.'
          : state.error && missing
            ? 'We could not retrieve subject records. Try again to reload this list.'
            : missing
              ? 'Subject records and totals will appear when an authorized data source is available.'
              : state.records?.length
                ? 'Try a different name, code, department, semester, type or status, or clear your filters.'
                : 'Create your first subject to build your institution’s subject catalogue.'}
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
          Add Subject
        </button>
      ) : null}
    </div>
  )
}
