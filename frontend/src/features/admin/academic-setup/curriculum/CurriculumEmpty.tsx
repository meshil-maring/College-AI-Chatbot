import { Database, FileStack, LockKeyhole, Search } from 'lucide-react'
import type { CurriculumState } from './useCurriculum.ts'

export default function CurriculumEmpty({ state }: { state: CurriculumState }) {
  const Icon = state.denied ? LockKeyhole : !state.programs ? Database : state.programs.length ? Search : FileStack
  return (
    <div className="curriculum-empty" role="status">
      <Icon aria-hidden="true" />
      <h2>
        {state.denied
          ? 'Curriculum access is unavailable'
          : !state.programs
            ? 'Program data is unavailable'
            : state.programs.length
              ? 'No programs match your filters'
              : 'No programs yet'}
      </h2>
      <p>
        {state.denied || !state.programs
          ? 'Readable program and subject catalogues are needed to display existing mappings.'
          : state.programs.length
            ? 'Try another name, program or status.'
            : 'Create a program in Academic Setup before mapping its subjects.'}
      </p>
      {Boolean(state.programs?.length) && (
        <button type="button" className="academic-secondary-button" onClick={state.clearFilters}>
          Clear filters
        </button>
      )}
    </div>
  )
}
