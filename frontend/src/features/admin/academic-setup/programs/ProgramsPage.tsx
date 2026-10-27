import { useEffect } from 'react'
import { ChevronRight, Info, Plus } from 'lucide-react'
import { usePrograms, type ProgramsContext } from './usePrograms.ts'
import { useProgramEditor } from './useProgramEditor.ts'
import ProgramSummary from './ProgramSummary.tsx'
import ProgramFilters from './ProgramFilters.tsx'
import ProgramTable from './ProgramTable.tsx'
import ProgramDrawer from './ProgramDrawer.tsx'
import './styles/programs.css'

interface Props extends ProgramsContext {
  createInitially: boolean
  onCreateHandled: () => void
  onOverview: () => void
}
export default function ProgramsPage({ createInitially, onCreateHandled, onOverview, ...context }: Props) {
  const state = usePrograms(context)
  const editor = useProgramEditor({
    ...context,
    catalogue: state.catalogue,
    busy: state.busy,
    refresh: state.query.refetch,
  })
  useEffect(() => {
    if (!createInitially || state.loading) return
    if (state.canCreate && !state.busy) editor.open('add')
    onCreateHandled()
  }, [createInitially, state.loading, state.canCreate, state.busy, editor, onCreateHandled])
  return (
    <section
      className={`academic-workspace programs-page${editor.panel && state.records ? ' has-drawer' : ''}`}
      aria-label="Programs management"
    >
      <nav className="academic-breadcrumbs" aria-label="Breadcrumb">
        <span>Home</span>
        <ChevronRight aria-hidden="true" />
        <button type="button" onClick={onOverview}>
          Academic Setup
        </button>
        <ChevronRight aria-hidden="true" />
        <span aria-current="page">Programs</span>
      </nav>
      <header className="academic-page-header">
        <div>
          <h1 tabIndex={-1}>Programs</h1>
          <p>Create and manage academic programs offered by each department.</p>
        </div>
        <button
          type="button"
          className="academic-primary-button"
          disabled={!state.canCreate || state.busy || editor.saving}
          onClick={() => editor.open('add')}
        >
          <Plus aria-hidden="true" /> Add Program
        </button>
      </header>
      <ProgramSummary state={state} />
      {(!context.canReadCatalogues || !state.manageable || !state.canCreate) && (
        <p className="program-access-note" role="status">
          <Info aria-hidden="true" />
          {!context.canReadCatalogues
            ? 'Your account does not have academic catalogue access. Counts and record actions are unavailable.'
            : !state.manageable
              ? 'Read-only access. You can view available programs; changes are unavailable.'
              : 'An available active department is required to create a program.'}
        </p>
      )}
      {state.error && (
        <div className="academic-request-error" role="alert">
          <p>
            {state.records
              ? 'Could not refresh programs. Showing the last loaded records; changes are unavailable until Retry succeeds.'
              : state.error}
          </p>
          <button
            type="button"
            className="academic-secondary-button"
            onClick={() => void state.query.refetch()}
            disabled={state.query.isFetching}
          >
            Retry
          </button>
        </div>
      )}
      {editor.notice && (
        <p className="program-save-notice" role="status">
          {editor.notice}
        </p>
      )}
      <ProgramFilters state={state} />
      <ProgramTable
        state={state}
        onCreate={() => editor.open('add')}
        onOpen={editor.open}
        onStatus={(record) => {
          editor.open('edit', record)
          editor.change('is_active', !record.is_active)
        }}
      />
      {editor.panel && state.records && <ProgramDrawer editor={editor} departments={state.departments} />}
    </section>
  )
}
