import { ChevronRight, Plus } from 'lucide-react'
import type { StructureContext } from '../structure/useAcademicStructure.ts'
import StructureState from '../structure/StructureState.tsx'
import { useBatches } from './useBatches.ts'
import { useBatchEditor } from './editor/useBatchEditor.ts'
import BatchSummary from './BatchSummary.tsx'
import BatchFilters from './BatchFilters.tsx'
import BatchTable from './BatchTable.tsx'
import BatchDrawer from './editor/BatchDrawer.tsx'
import './styles/batches.css'

export default function BatchesPage({ onOverview, ...context }: StructureContext & { onOverview: () => void }) {
  const state = useBatches(context)
  const editor = useBatchEditor(state)
  return (
    <section
      className={`academic-workspace batches-page${editor.panel ? ' has-drawer' : ''}`}
      aria-label="Batches management"
    >
      <nav className="academic-breadcrumbs" aria-label="Breadcrumb">
        <span>Home</span>
        <ChevronRight aria-hidden="true" />
        <button type="button" onClick={onOverview}>
          Academic Setup
        </button>
        <ChevronRight aria-hidden="true" />
        <span aria-current="page">Batches</span>
      </nav>
      <header className="academic-page-header">
        <div>
          <h1 tabIndex={-1}>Batches</h1>
          <p>Manage student batches for each program and academic year.</p>
        </div>
        <button
          type="button"
          className="academic-primary-button"
          disabled={!state.canCreate || editor.saving}
          onClick={() => editor.open('add')}
        >
          <Plus aria-hidden="true" />
          Add Batch
        </button>
      </header>
      <BatchSummary records={state.records} available={state.available} />
      <StructureState state={state.source} />
      {!state.loading && state.canManage && !state.canCreate && (
        <p className="batch-integration-note">
          Create an active program, academic year and published curriculum before adding a batch.
        </p>
      )}
      {state.notice && (
        <p className="batch-save-notice" role="status">
          {state.notice}
        </p>
      )}
      <BatchFilters state={state} />
      <BatchTable state={state} onOpen={editor.open} />
      {editor.panel && <BatchDrawer editor={editor} />}
    </section>
  )
}
