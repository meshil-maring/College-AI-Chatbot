import { useEffect } from 'react'
import { ChevronRight, Info, Plus } from 'lucide-react'
import { useSubjects, type SubjectsContext } from './useSubjects.ts'
import { useSubjectEditor } from './useSubjectEditor.ts'
import SubjectSummary from './SubjectSummary.tsx'
import SubjectFilters from './SubjectFilters.tsx'
import SubjectTable from './SubjectTable.tsx'
import SubjectDrawer from './SubjectDrawer.tsx'
import './styles/subjects.css'

interface Props extends SubjectsContext {
  createInitially: boolean
  onCreateHandled: () => void
  onOverview: () => void
}
export default function SubjectsPage({ createInitially, onCreateHandled, onOverview, ...context }: Props) {
  const state = useSubjects(context)
  const editor = useSubjectEditor({
    ...context,
    catalogue: state.catalogue,
    busy: state.busy,
    refresh: state.query.refetch,
  })
  useEffect(() => {
    if (!createInitially || state.loading || state.query.isFetching) return
    if (state.canCreate && !state.busy) editor.open('add')
    onCreateHandled()
  }, [createInitially, state.loading, state.query.isFetching, state.canCreate, state.busy, editor, onCreateHandled])
  return (
    <section
      className={`academic-workspace subjects-page${editor.panel && state.records ? ' has-drawer' : ''}`}
      aria-label="Subjects management"
    >
      <nav className="academic-breadcrumbs" aria-label="Breadcrumb">
        <span>Home</span>
        <ChevronRight aria-hidden="true" />
        <button type="button" onClick={onOverview}>
          Academic Setup
        </button>
        <ChevronRight aria-hidden="true" />
        <span aria-current="page">Subjects</span>
      </nav>
      <header className="academic-page-header">
        <div>
          <h1 tabIndex={-1}>Subjects</h1>
          <p>Manage subject catalogue and subject details for your institution.</p>
        </div>
        <button
          type="button"
          className="academic-primary-button"
          disabled={!state.canCreate || state.busy || editor.saving}
          onClick={() => editor.open('add')}
        >
          <Plus aria-hidden="true" /> Add Subject
        </button>
      </header>
      <SubjectSummary state={state} />
      {(!context.canReadCatalogues || !state.manageable || !state.canCreate) && (
        <p className="subject-access-note" role="status">
          <Info aria-hidden="true" />
          {!context.canReadCatalogues
            ? 'Your account does not have academic catalogue access. Counts and record actions are unavailable.'
            : !state.manageable
              ? 'Read-only access. You can view available subjects; changes are unavailable.'
              : 'An available active department is required to create a subject.'}
        </p>
      )}
      {state.error && (
        <div className="academic-request-error" role="alert">
          <p>
            {state.records
              ? 'Could not refresh subjects. Showing the last loaded records; changes are unavailable until Retry succeeds.'
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
        <p className="subject-save-notice" role="status">
          {editor.notice}
        </p>
      )}
      <SubjectFilters state={state} />
      <SubjectTable
        state={state}
        onCreate={() => editor.open('add')}
        onOpen={editor.open}
        onStatus={(record) => {
          editor.open('edit', record)
          editor.change('is_active', !record.is_active)
        }}
      />
      {editor.panel && state.records && (
        <SubjectDrawer editor={editor} departments={state.departments} assignments={state.assignments} />
      )}
    </section>
  )
}
