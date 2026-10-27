import { ChevronRight, Info } from 'lucide-react'
import { useCurriculum, type CurriculumContext } from './useCurriculum.ts'
import type { CurriculumTab } from './curriculumModel.ts'
import CurriculumSummary from './CurriculumSummary.tsx'
import CurriculumFilters from './CurriculumFilters.tsx'
import CurriculumTabs from './CurriculumTabs.tsx'
import CurriculumList from './CurriculumList.tsx'
import CurriculumDetail from './CurriculumDetail.tsx'
import CurriculumEmpty from './CurriculumEmpty.tsx'
import { useMappingEditor } from './editor/useMappingEditor.ts'
import MappingDrawer from './editor/MappingDrawer.tsx'
import './styles/curriculum.css'

const tabs: { id: CurriculumTab; label: string }[] = [
  { id: 'list', label: 'Curriculum List' },
  { id: 'structure', label: 'Curriculum Structure' },
  { id: 'mapping', label: 'Subject Mapping' },
]
export function ExistingCurriculumMappings({
  initialTab = 'list',
  onOverview,
  ...context
}: CurriculumContext & { initialTab?: CurriculumTab; onOverview: () => void }) {
  const state = useCurriculum(context, initialTab)
  const editor = useMappingEditor(context, state)
  return (
    <section
      className={`academic-workspace curriculum-page${editor.panel ? ' has-drawer' : ''}`}
      aria-label="Curriculum management"
    >
      <nav className="academic-breadcrumbs" aria-label="Breadcrumb">
        <span>Home</span>
        <ChevronRight aria-hidden="true" />
        <button type="button" onClick={onOverview}>
          Academic Setup
        </button>
        <ChevronRight aria-hidden="true" />
        <span aria-current="page">Curriculum</span>
      </nav>
      <header className="academic-page-header">
        <div>
          <h1 tabIndex={-1}>Curriculum</h1>
          <p>Define curriculum structure and map subjects to semesters for each program.</p>
        </div>
      </header>
      <CurriculumSummary state={state} />
      <p className="curriculum-integration-note">
        <Info aria-hidden="true" />
        <span>
          Existing program–subject mappings are retained separately from versioned curricula. Status filters use program
          status.
        </span>
      </p>
      {!context.canReadCatalogues && (
        <p className="curriculum-access-note" role="status">
          Your account does not have academic catalogue access. Live records and mapping actions are unavailable.
        </p>
      )}
      {!state.loading && context.canReadCatalogues && !state.manageable && (
        <p className="curriculum-access-note" role="status">
          Read-only access. You can view available mappings; changes are unavailable.
        </p>
      )}
      {state.error && (
        <div className="academic-request-error" role="alert">
          <p>
            {state.programs
              ? 'Could not refresh curriculum mappings. Showing the last loaded records; changes are unavailable until Retry succeeds.'
              : state.error}
          </p>
          <button
            type="button"
            className="academic-secondary-button"
            disabled={state.query.isFetching}
            onClick={() => void state.query.refetch()}
          >
            Retry
          </button>
        </div>
      )}
      {editor.notice && (
        <p className="curriculum-save-notice" role="status">
          {editor.notice}
        </p>
      )}
      <CurriculumTabs
        items={tabs}
        value={state.tab}
        onChange={state.setTab}
        prefix="curriculum"
        label="Curriculum views"
      />
      <div id="curriculum-panel" role="tabpanel" aria-labelledby={`curriculum-${state.tab}`}>
        <>
          <CurriculumFilters state={state} />
          {state.loading ? (
            <div className="curriculum-loading" role="status">
              Loading curriculum mappings…
              {Array.from({ length: 5 }, (_, index) => (
                <span className="curriculum-skeleton" key={index} aria-hidden="true" />
              ))}
            </div>
          ) : !state.filtered.length ? (
            <CurriculumEmpty state={state} />
          ) : (
            <div className="curriculum-split">
              <CurriculumList state={state} />
              <CurriculumDetail
                state={state}
                onAdd={(semesterId) => editor.open(undefined, semesterId)}
                onEdit={(link) => editor.open(link)}
                onStatus={(link) => editor.open(link, undefined, true)}
              />
            </div>
          )}
        </>
      </div>
      {editor.panel && state.links && <MappingDrawer state={state} editor={editor} />}
    </section>
  )
}
