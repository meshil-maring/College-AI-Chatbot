import { ChevronRight, Plus } from 'lucide-react'
import type { StructureContext } from '../structure/useAcademicStructure.ts'
import StructureState from '../structure/StructureState.tsx'
import { useSections } from './useSections.ts'
import { useSectionEditor } from './editor/useSectionEditor.ts'
import SectionSummary from './SectionSummary.tsx'
import SectionFilters from './SectionFilters.tsx'
import SectionTable from './SectionTable.tsx'
import SectionDrawer from './editor/SectionDrawer.tsx'
import './styles/sections.css'

export default function SectionsPage({ onOverview, ...context }: StructureContext & { onOverview: () => void }) {
  const state = useSections(context)
  const editor = useSectionEditor(state)
  return (
    <section
      className={`academic-workspace sections-page${editor.panel ? ' has-drawer' : ''}`}
      aria-label="Sections management"
    >
      <nav className="academic-breadcrumbs" aria-label="Breadcrumb">
        <span>Home</span>
        <ChevronRight aria-hidden="true" />
        <button type="button" onClick={onOverview}>
          Academic Setup
        </button>
        <ChevronRight aria-hidden="true" />
        <span aria-current="page">Sections</span>
      </nav>
      <header className="academic-page-header">
        <div>
          <h1 tabIndex={-1}>Sections</h1>
          <p>Manage sections for each batch and organize students into groups.</p>
        </div>
        <button
          type="button"
          className="academic-primary-button"
          disabled={!state.canCreate || editor.saving}
          onClick={() => editor.open('add')}
        >
          <Plus aria-hidden="true" />
          Add Section
        </button>
      </header>
      <SectionSummary records={state.records} available={state.available} />
      <StructureState state={state.source} />
      {!state.loading && state.canManage && !state.canCreate && (
        <p className="section-integration-note">
          Create an active batch, program semester and dated teaching term before adding a section.
        </p>
      )}
      {state.notice && (
        <p className="section-save-notice" role="status">
          {state.notice}
        </p>
      )}
      <SectionFilters state={state} />
      <SectionTable state={state} onOpen={editor.open} />
      {editor.panel && <SectionDrawer editor={editor} />}
    </section>
  )
}
