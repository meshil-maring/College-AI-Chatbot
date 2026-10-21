import { Filter, Search } from 'lucide-react'
import { type ReviewStatus } from '../studentImport.ts'
import type { StudentImportModel } from './useStudentImport.ts'
import { statuses } from './useStudentImport.ts'
export function ImportToolbar({ model }: { model: StudentImportModel }) {
  const { filter, setFilter, search, setSearch, setPage, onlySelected, showFilters, setShowFilters, reviewed, counts } =
    model
  return (
    <div className="students-toolbar">
      <div className="students-tabs" role="group" aria-label="Validation status">
        <button
          className={filter === 'all' ? 'active' : ''}
          onClick={() => {
            setFilter('all')
            setPage(1)
          }}
        >
          All Records ({reviewed.length})
        </button>
        {(Object.keys(statuses) as ReviewStatus[]).map((status) => {
          const { Icon, label } = statuses[status]
          return (
            <button
              key={status}
              className={filter === status ? 'active' : ''}
              onClick={() => {
                setFilter(status)
                setPage(1)
              }}
            >
              <Icon className={status} />
              {label} ({counts[status]})
            </button>
          )
        })}
      </div>
      <div className="students-table-actions">
        <label className="students-search">
          <Search />
          <input
            type="search"
            aria-label="Search import records"
            placeholder="Search name, register no, roll no…"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
          />
        </label>
        <button
          className={`students-button ${showFilters ? 'is-active' : ''}`}
          aria-expanded={showFilters}
          aria-controls="student-import-filters"
          onClick={() => setShowFilters(!showFilters)}
        >
          <Filter />
          Filters{onlySelected ? ' (1)' : ''}
        </button>
      </div>
    </div>
  )
}
