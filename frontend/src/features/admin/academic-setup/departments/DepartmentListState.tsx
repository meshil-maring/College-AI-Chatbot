import { Building2, Database, LockKeyhole, Search, TriangleAlert } from 'lucide-react'
import type { useDepartments } from './useDepartments.ts'

export default function DepartmentListState({
  state,
  onCreate,
}: {
  state: ReturnType<typeof useDepartments>
  onCreate: () => void
}) {
  const missing = !state.records
  const Icon = state.denied
    ? LockKeyhole
    : state.error
      ? TriangleAlert
      : missing
        ? Database
        : state.records?.length
          ? Search
          : Building2
  const title = state.denied
    ? 'Department access is unavailable'
    : state.error && missing
      ? 'Departments could not be loaded'
      : missing
        ? 'Department data is not connected'
        : state.records?.length
          ? 'No departments match your filters'
          : 'No departments yet'
  return (
    <div className="department-list-state">
      <span className="department-state-icon">
        <Icon aria-hidden="true" />
      </span>
      <h2>{title}</h2>
      <p>
        {state.denied
          ? 'Your account cannot view these department records. Contact your institution administrator.'
          : state.error && missing
            ? 'We couldn’t retrieve department records. Try again to reload this list.'
            : missing
              ? 'Department records and totals will appear when an authorized data source is available.'
              : state.records?.length
                ? `Try a different name or code${state.search ? ` instead of “${state.search}”` : ''}, or clear your filters.`
                : 'Create your first department to organize your institution’s academic structure.'}
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
      ) : state.manageable ? (
        <button type="button" className="academic-primary-button" onClick={onCreate} disabled={state.busy}>
          Add Department
        </button>
      ) : null}
    </div>
  )
}
