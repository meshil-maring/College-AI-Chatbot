import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { StudentImportModel } from './useStudentImport.ts'
import { PAGE_SIZE } from './useStudentImport.ts'
export function ImportPagination({ model }: { model: StudentImportModel }) {
  const { setPage, filtered, totalPages, currentPage } = model
  return (
    <div className="students-pagination">
      <p>
        Showing {filtered.length ? (currentPage - 1) * PAGE_SIZE + 1 : 0}–
        {Math.min(currentPage * PAGE_SIZE, filtered.length)} of {filtered.length} records
      </p>
      <div>
        <button
          className="students-page"
          aria-label="Previous page"
          disabled={currentPage === 1}
          onClick={() => setPage(currentPage - 1)}
        >
          <ChevronLeft />
        </button>
        {Array.from(
          { length: Math.min(5, totalPages) },
          (_, index) => Math.min(Math.max(1, currentPage - 2), Math.max(1, totalPages - 4)) + index,
        ).map((number) => (
          <button
            className={`students-page ${currentPage === number ? 'active' : ''}`}
            aria-label={`Page ${number}`}
            aria-current={currentPage === number ? 'page' : undefined}
            key={number}
            onClick={() => setPage(number)}
          >
            {number}
          </button>
        ))}
        <button
          className="students-page"
          aria-label="Next page"
          disabled={currentPage === totalPages}
          onClick={() => setPage(currentPage + 1)}
        >
          <ChevronRight />
        </button>
      </div>
    </div>
  )
}
