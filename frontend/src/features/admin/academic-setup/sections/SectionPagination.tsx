import { ChevronLeft, ChevronRight } from 'lucide-react'
import { SECTION_PAGE_SIZE } from './sectionModel.ts'
import type { SectionsState } from './useSections.ts'

export default function SectionPagination({ state }: { state: SectionsState }) {
  const first = state.filtered.length ? (state.page - 1) * SECTION_PAGE_SIZE + 1 : 0
  const last = Math.min(state.page * SECTION_PAGE_SIZE, state.filtered.length)
  return (
    <div className="section-pagination">
      <p role="status">
        Showing {first} to {last} of {state.filtered.length} sections
      </p>
      <nav aria-label="Section pagination">
        <button
          type="button"
          aria-label="Previous page"
          disabled={state.page === 1}
          onClick={() => state.setPage(state.page - 1)}
        >
          <ChevronLeft aria-hidden="true" />
        </button>
        {Array.from({ length: state.pages }, (_, index) => index + 1).map((page) => (
          <button
            type="button"
            key={page}
            aria-label={`Page ${page}`}
            aria-current={state.page === page ? 'page' : undefined}
            onClick={() => state.setPage(page)}
          >
            {page}
          </button>
        ))}
        <button
          type="button"
          aria-label="Next page"
          disabled={state.page === state.pages}
          onClick={() => state.setPage(state.page + 1)}
        >
          <ChevronRight aria-hidden="true" />
        </button>
      </nav>
    </div>
  )
}
