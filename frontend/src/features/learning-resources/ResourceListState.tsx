import { BookOpen } from 'lucide-react'
import type { ResourcesState } from './data/useResources.ts'
import { resourceError } from '../../services/knowledge/resources.ts'

export default function ResourceListState({ state }: { state: ResourcesState }) {
  const { query, data } = state
  if (!state.enabled)
    return (
      <p role="status" className="lr-empty">
        You do not have access to this resource view.
      </p>
    )
  if (!data && query.isLoading)
    return (
      <div role="status" aria-label="Loading learning resources" className="lr-skeletons">
        <p>Loading learning resources…</p>
        {[1, 2, 3].map((item) => (
          <div key={item} className="lr-skeleton" aria-hidden="true" />
        ))}
      </div>
    )
  if (!data && query.fetchStatus === 'paused')
    return (
      <p role="status" className="lr-empty">
        You appear to be offline. Learning resources will load when your connection returns.
      </p>
    )
  if (!data && query.isError)
    return (
      <div className="lr-empty" role="alert">
        <p>{resourceError(query.error)}</p>
        <button type="button" className="lr-secondary" onClick={() => void query.refetch()}>
          Retry loading resources
        </button>
      </div>
    )
  if (!data)
    return (
      <p role="status" className="lr-empty">
        Sign in to your institution to load resources.
      </p>
    )
  if (data.items.length === 0)
    return (
      <div className="lr-empty">
        <BookOpen size={28} aria-hidden="true" />
        <h2>
          {state.view === 'library'
            ? 'No published resources yet'
            : state.view === 'own'
              ? 'No submissions yet'
              : 'No revisions to review'}
        </h2>
        <p>
          {state.view === 'library'
            ? 'Resources appear here after publication when they match your audience.'
            : state.view === 'own'
              ? 'Add a resource to save your first private draft.'
              : 'Submitted drafts and publication history will appear here.'}
        </p>
        {state.offset > 0 && (
          <button type="button" className="lr-secondary" onClick={() => state.setOffset(0)}>
            Return to first page
          </button>
        )}
      </div>
    )
  if (!state.rows?.length)
    return (
      <div className="lr-empty">
        <h2>No matches on this page</h2>
        <p>Search and filters apply to the current page of results.</p>
        <button type="button" className="lr-secondary" onClick={state.clearFilters}>
          Clear filters
        </button>
      </div>
    )
  return null
}
