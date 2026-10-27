import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { CurriculumState } from './useCurriculum.ts'
import { CURRICULUM_PAGE_SIZE } from './curriculumModel.ts'
import CurriculumBadge from './CurriculumBadge.tsx'

export default function CurriculumList({ state }: { state: CurriculumState }) {
  return (
    <section className="curriculum-program-list" aria-label="Programs and existing mappings">
      <div className="curriculum-program-cards">
        {state.rows.map((program) => {
          const links = state.links?.filter((link) => link.program_id === program.program_id)
          const semesters = links
            ? new Set(links.flatMap((link) => (link.semester_id ? [link.semester_id] : []))).size
            : undefined
          return (
            <button
              type="button"
              className={`curriculum-program-card${state.selected?.program_id === program.program_id ? ' is-selected' : ''}`}
              key={program.program_id}
              aria-pressed={state.selected?.program_id === program.program_id}
              onClick={() => state.setSelectedId(program.program_id)}
            >
              <span className="curriculum-program-copy">
                <strong>{program.name}</strong>
                <span className="curriculum-version-tag">Unversioned</span>
                <small>
                  {program.code}
                  <span aria-hidden="true"> | </span>
                  {links ? `${links.length} subject mappings` : 'Mappings unavailable'}
                  <span aria-hidden="true"> | </span>
                  {semesters === undefined ? 'Terms unavailable' : `${semesters} dated terms`}
                </small>
              </span>
              <span title="Program status">
                <CurriculumBadge active={program.is_active} />
              </span>
              <ChevronRight aria-hidden="true" />
            </button>
          )
        })}
      </div>
      <footer className="curriculum-pagination">
        <p role="status">
          Showing {(state.page - 1) * CURRICULUM_PAGE_SIZE + 1} to{' '}
          {Math.min(state.page * CURRICULUM_PAGE_SIZE, state.filtered.length)} of {state.filtered.length} programs
        </p>
        <nav aria-label="Curriculum program pagination">
          <button
            type="button"
            aria-label="Previous curriculum page"
            disabled={state.page <= 1}
            onClick={() => state.setPage(state.page - 1)}
          >
            <ChevronLeft aria-hidden="true" />
          </button>
          {[...new Set([1, state.page, state.pages])].map((page) => (
            <button
              type="button"
              key={page}
              aria-label={`Curriculum page ${page}`}
              aria-current={page === state.page ? 'page' : undefined}
              onClick={() => state.setPage(page)}
            >
              {page}
            </button>
          ))}
          <button
            type="button"
            aria-label="Next curriculum page"
            disabled={state.page >= state.pages}
            onClick={() => state.setPage(state.page + 1)}
          >
            <ChevronRight aria-hidden="true" />
          </button>
        </nav>
      </footer>
    </section>
  )
}
