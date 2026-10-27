import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { SubjectsState } from './useSubjects.ts'
import { SUBJECT_PAGE_SIZE } from './subjectModel.ts'

export default function SubjectPagination({ state }: { state: SubjectsState }) {
  const { page, pages, filtered, loading } = state
  const visible = [...new Set([1, page - 1, page, page + 1, pages])].filter((value) => value > 0 && value <= pages)
  return (
    <footer className="subject-pagination">
      <p role="status">
        {loading
          ? 'Loading subjects…'
          : !state.records
            ? 'Count unavailable'
            : filtered.length
              ? `Showing ${(page - 1) * SUBJECT_PAGE_SIZE + 1} to ${Math.min(page * SUBJECT_PAGE_SIZE, filtered.length)} of ${filtered.length} subjects`
              : '0 matching subjects'}
      </p>
      <nav aria-label="Subject pagination">
        <button
          type="button"
          aria-label="Previous subject page"
          disabled={page <= 1 || loading}
          onClick={() => state.setPage(page - 1)}
        >
          <ChevronLeft aria-hidden="true" />
        </button>
        {visible.map((value, index) => (
          <span className="subject-page-item" key={value}>
            {index > 0 && value - visible[index - 1] > 1 && <span aria-hidden="true">…</span>}
            <button
              type="button"
              aria-label={`Subject page ${value}`}
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
          aria-label="Next subject page"
          disabled={page >= pages || loading}
          onClick={() => state.setPage(page + 1)}
        >
          <ChevronRight aria-hidden="true" />
        </button>
      </nav>
    </footer>
  )
}
