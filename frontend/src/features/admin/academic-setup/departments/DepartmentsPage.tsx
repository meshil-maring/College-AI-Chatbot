import { useEffect } from 'react'
import { ChevronRight, Info, Plus } from 'lucide-react'
import { useDepartments, type DepartmentsContext } from './useDepartments.ts'
import { useDepartmentEditor } from './useDepartmentEditor.ts'
import DepartmentSummary from './DepartmentSummary.tsx'
import DepartmentFilters from './DepartmentFilters.tsx'
import DepartmentTable from './DepartmentTable.tsx'
import DepartmentDrawer from './DepartmentDrawer.tsx'
import AcademicDeleteDialog from '../deletion/AcademicDeleteDialog.tsx'
import { useAcademicDeletion } from '../deletion/useAcademicDeletion.ts'
import './styles/departments.css'

interface Props extends DepartmentsContext {
  createInitially: boolean
  onCreateHandled: () => void
  onOverview: () => void
}
export default function DepartmentsPage({ createInitially, onCreateHandled, onOverview, ...context }: Props) {
  const state = useDepartments(context)
  const editor = useDepartmentEditor({
    ...context,
    catalogue: state.catalogue,
    busy: state.busy,
    refresh: state.query.refetch,
  })
  const deletion = useAcademicDeletion({
    entity: 'departments',
    ...context,
    catalogue: state.catalogue,
    busy: state.busy || editor.saving,
    refresh: state.query.refetch,
  })
  useEffect(() => {
    if (!createInitially || state.loading) return
    if (state.manageable && !state.busy) editor.open('add')
    onCreateHandled()
  }, [createInitially, state.loading, state.manageable, state.busy, editor, onCreateHandled])
  return (
    <section
      className={`academic-workspace departments-page${editor.panel && state.records ? ' has-drawer' : ''}`}
      aria-label="Departments management"
    >
      <nav className="academic-breadcrumbs" aria-label="Breadcrumb">
        <span>Home</span>
        <ChevronRight aria-hidden="true" />
        <button type="button" onClick={onOverview}>
          Academic Setup
        </button>
        <ChevronRight aria-hidden="true" />
        <span aria-current="page">Departments</span>
      </nav>
      <header className="academic-page-header">
        <div>
          <h1 tabIndex={-1}>Departments</h1>
          <p>Create and manage academic departments for your institution.</p>
        </div>
        <button
          type="button"
          className="academic-primary-button"
          disabled={!state.manageable || state.busy || editor.saving || deletion.saving}
          onClick={() => editor.open('add')}
          title={state.manageable ? undefined : 'Department creation is unavailable for this account.'}
        >
          <Plus aria-hidden="true" />
          Add Department
        </button>
      </header>
      <DepartmentSummary records={state.records} loading={state.loading} />
      {!context.canReadCatalogues ? (
        <p className="department-access-note" role="status">
          <Info aria-hidden="true" />
          Your account does not have academic catalogue access. Counts and record actions are unavailable.
        </p>
      ) : state.records && !state.manageable ? (
        <p className="department-access-note">
          <Info aria-hidden="true" />
          Read-only access. You can view departments; changes are unavailable.
        </p>
      ) : null}
      {state.error && (
        <div className="academic-request-error" role="alert">
          <p>
            {state.records
              ? 'Could not refresh departments. Showing the last loaded records; changes are unavailable until Retry succeeds.'
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
        <p className="department-save-notice" role="status">
          {editor.notice}
        </p>
      )}
      {deletion.notice && (
        <p className="department-save-notice" role="status">
          {deletion.notice}
        </p>
      )}
      <DepartmentFilters state={state} />
      <DepartmentTable
        state={state}
        onCreate={() => editor.open('add')}
        onOpen={editor.open}
        onDelete={deletion.open}
        saving={editor.saving || deletion.saving}
      />
      {editor.panel && state.records && <DepartmentDrawer editor={editor} catalogue={state.catalogue} />}
      {deletion.record && state.records && <AcademicDeleteDialog deletion={deletion} />}
    </section>
  )
}
