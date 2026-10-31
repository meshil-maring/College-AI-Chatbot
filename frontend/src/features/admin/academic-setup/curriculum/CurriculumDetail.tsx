import { Clock3, MoreHorizontal, Pencil, Plus } from 'lucide-react'
import type { CurriculumState } from './useCurriculum.ts'
import type { DetailTab } from './curriculumModel.ts'
import CurriculumBadge from './CurriculumBadge.tsx'
import CurriculumTabs from './CurriculumTabs.tsx'
import SemesterStructure from './detail/SemesterStructure.tsx'
import MappingTable, { type MappingActions } from './detail/MappingTable.tsx'
import ProgramOverview from './detail/ProgramOverview.tsx'

const tabs: { id: DetailTab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'structure', label: 'Semester Structure' },
  { id: 'subjects', label: 'Subject List' },
  { id: 'outcomes', label: 'Program Outcomes' },
]
export default function CurriculumDetail({ state, ...actions }: { state: CurriculumState } & MappingActions) {
  const program = state.selected
  if (!program) return null
  const detailTab = state.tab === 'structure' ? 'structure' : state.tab === 'mapping' ? 'subjects' : state.detailTab
  return (
    <section className="curriculum-detail" aria-label="Selected program curriculum">
      <header>
        <div>
          <h2>
            {program.name}{' '}
            <span title="Program status">
              <CurriculumBadge active={program.is_active} />
            </span>
          </h2>
          <p>
            Legacy program mappings<span aria-hidden="true"> | </span>
            {program.code}
            <span aria-hidden="true"> | </span>Unversioned
          </p>
        </div>
        <button
          type="button"
          className="academic-secondary-button"
          disabled
          title="Curriculum version editing is not connected"
        >
          <Pencil aria-hidden="true" />
          Edit
        </button>
        <details
          className="curriculum-more"
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              event.currentTarget.open = false
              event.currentTarget.querySelector('summary')?.focus()
            }
          }}
        >
          <summary aria-label="More curriculum actions">
            <MoreHorizontal aria-hidden="true" />
          </summary>
          <div>
            <button
              type="button"
              onClick={(event) => {
                event.currentTarget.closest('details')?.removeAttribute('open')
                state.setTab('list')
                state.setDetailTab('overview')
              }}
            >
              View program overview
            </button>
          </div>
        </details>
      </header>
      {state.tab === 'list' && (
        <CurriculumTabs
          items={tabs}
          value={detailTab}
          onChange={state.setDetailTab}
          prefix="curriculum-detail"
          label="Curriculum details"
        />
      )}
      <div
        id="curriculum-detail-panel"
        role={state.tab === 'list' ? 'tabpanel' : undefined}
        aria-labelledby={state.tab === 'list' ? `curriculum-detail-${detailTab}` : undefined}
      >
        {detailTab === 'overview' ? (
          <ProgramOverview state={state} />
        ) : detailTab === 'outcomes' ? (
          <div className="curriculum-empty">
            <Clock3 aria-hidden="true" />
            <h3>Program outcomes are not connected</h3>
            <p>Outcomes will appear when an approved curriculum service is available.</p>
          </div>
        ) : detailTab === 'structure' ? (
          <SemesterStructure key={program.program_id} state={state} {...actions} />
        ) : (
          <div className="curriculum-subject-list">
            <div className="curriculum-subject-list-header">
              <h3>Subject Mapping</h3>
              <button
                type="button"
                className="curriculum-outline-button"
                disabled={!state.canAdd}
                onClick={() => actions.onAdd()}
              >
                <Plus aria-hidden="true" />
                Add Subject
              </button>
            </div>
            {state.selectedLinks?.length ? (
              <MappingTable state={state} links={state.selectedLinks} {...actions} />
            ) : (
              <p className="curriculum-detail-note">
                {state.selectedLinks
                  ? 'No subject mappings yet.'
                  : 'Subject mappings are unavailable for this account.'}
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
