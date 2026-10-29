import { RefreshCw, Search } from 'lucide-react'
import type { ResourcesState } from './data/useResources.ts'
import { stateLabels } from './resourcePresentation.ts'

export default function ResourceToolbar({ state }: { state: ResourcesState }) {
  return (
    <div className="lr-toolbar">
      <label className="lr-search">
        <span>Search this page</span>
        <span className="lr-search-input">
          <Search size={18} aria-hidden="true" />
          <input
            type="search"
            value={state.search}
            placeholder="Search resources…"
            onChange={(event) => state.setSearch(event.target.value)}
          />
        </span>
      </label>
      <label>
        Audience
        <select value={state.audience} onChange={(event) => state.setAudience(event.target.value)}>
          <option value="all">All audiences</option>
          <option value="public">Public</option>
          <option value="authenticated">Institution members</option>
          <option value="restricted">Selected roles</option>
        </select>
      </label>
      {state.view !== 'library' && (
        <label>
          Review status
          <select value={state.status} onChange={(event) => state.setStatus(event.target.value)}>
            <option value="all">All statuses</option>
            {Object.entries(stateLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      )}
      <button
        type="button"
        className="lr-secondary"
        disabled={state.query.isFetching}
        onClick={() => void state.query.refetch()}
      >
        <RefreshCw size={16} aria-hidden="true" />
        {state.query.isFetching ? 'Updating…' : 'Refresh'}
      </button>
    </div>
  )
}
