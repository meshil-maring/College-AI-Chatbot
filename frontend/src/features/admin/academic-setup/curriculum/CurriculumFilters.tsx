import { Search, X } from 'lucide-react'
import type { CurriculumState } from './useCurriculum.ts'
import type { CurriculumSort, CurriculumStatus } from './curriculumModel.ts'

export default function CurriculumFilters({ state }: { state: CurriculumState }) {
  return (
    <div className="curriculum-filters" role="search" aria-label="Filter curriculum programs">
      <label className="curriculum-search">
        <Search aria-hidden="true" />
        <span className="sr-only">Search curriculum programs</span>
        <input
          type="search"
          placeholder="Search curriculum by name or program..."
          value={state.search}
          disabled={!state.programs}
          onChange={(event) => state.setSearch(event.target.value)}
        />
        {state.search && (
          <button type="button" aria-label="Clear curriculum search" onClick={() => state.setSearch('')}>
            <X aria-hidden="true" />
          </button>
        )}
      </label>
      <label>
        <span>Program</span>
        <select
          value={state.programId}
          disabled={!state.programs}
          onChange={(event) => state.setProgram(event.target.value)}
        >
          <option value="">All Programs</option>
          {state.programs?.map((program) => (
            <option key={program.program_id} value={program.program_id}>
              {program.name} ({program.code})
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Status</span>
        <select
          value={state.status}
          disabled={!state.programs}
          title="Filters program status"
          onChange={(event) => state.setStatus(event.target.value as CurriculumStatus)}
        >
          <option value="all">All Status</option>
          <option value="active">Active programs</option>
          <option value="inactive">Inactive programs</option>
        </select>
      </label>
      <label>
        <span>Sort by</span>
        <select
          value={state.sort}
          disabled={!state.programs}
          onChange={(event) => state.setSort(event.target.value as CurriculumSort)}
        >
          <option value="name-asc">Name (A - Z)</option>
          <option value="name-desc">Name (Z - A)</option>
          <option value="code-asc">Program code</option>
        </select>
      </label>
    </div>
  )
}
