import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { ProgramsState } from './usePrograms.ts'
import { PROGRAM_PAGE_SIZE } from './programModel.ts'

export default function ProgramPagination({ state }: { state: ProgramsState }) {
  const { page, pages, filtered, loading } = state
  const visible = [...new Set([1, page - 1, page, page + 1, pages])].filter((value) => value > 0 && value <= pages)
  return (
    <footer className="program-pagination">
      <p role="status">
        {loading
          ? 'Loading programs…'
          : !state.records
            ? 'Count unavailable'
            : filtered.length
              ? `Showing ${(page - 1) * PROGRAM_PAGE_SIZE + 1} to ${Math.min(page * PROGRAM_PAGE_SIZE, filtered.length)} of ${filtered.length} programs`
              : '0 matching programs'}
      </p>
      <nav aria-label="Program pagination">
        <button
          type="button"
          aria-label="Previous program page"
          disabled={page <= 1 || loading}
          onClick={() => state.setPage(page - 1)}
        >
          <ChevronLeft aria-hidden="true" />
        </button>
        {visible.map((value, index) => (
          <span className="program-page-item" key={value}>
            {index > 0 && value - visible[index - 1] > 1 && <span aria-hidden="true">…</span>}
            <button
              type="button"
              aria-label={`Program page ${value}`}
              aria-current={page === value ? 'page' : undefined}
              disabled={loading}
              onClick={() => state.setPage(value)}
            >
              {value}
            </button>
          </span>
        ))}
        <button
          type="button"
          aria-label="Next program page"
          disabled={page >= pages || loading}
          onClick={() => state.setPage(page + 1)}
        >
          <ChevronRight aria-hidden="true" />
        </button>
      </nav>
    </footer>
  )
}
