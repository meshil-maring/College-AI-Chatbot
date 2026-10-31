import { ChevronRight, Plus } from 'lucide-react'
import { useState } from 'react'
import StudentEnrollmentPage from '../registration/StudentEnrollmentPage.tsx'
import type { StructureContext } from '../structure/useAcademicStructure.ts'
import StructureState from '../structure/StructureState.tsx'
import { useSections } from './useSections.ts'
import { useSectionEditor } from './editor/useSectionEditor.ts'
import SectionSummary from './SectionSummary.tsx'
import SectionFilters from './SectionFilters.tsx'
import SectionTable from './SectionTable.tsx'
import SectionDrawer from './editor/SectionDrawer.tsx'
import { useAcademicDeletion } from '../deletion/useAcademicDeletion.ts'
import AcademicDeleteDialog from '../deletion/AcademicDeleteDialog.tsx'
import './styles/sections.css'

export default function SectionsPage({
  onOverview,
  onEnrollment,
  ...context
}: StructureContext & { onOverview: () => void; onEnrollment?: () => void }) {
  const state = useSections(context)
  const editor = useSectionEditor(state)
  const deletion = useAcademicDeletion({
    ...context,
    entity: 'academic_sections',
    catalogue: state.catalogue,
    structure: state.structure,
    busy: state.busy || state.write.saving,
    refresh: state.refresh,
  })
  const [enrollment, setEnrollment] = useState(false)
  if (enrollment) return <StudentEnrollmentPage context={context} onBack={() => setEnrollment(false)} />
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
          <p>
            A section is a class group within a batch for one program semester and dated teaching term. Create one for
            each group that needs its own enrollment and subject offerings.
          </p>
        </div>
        <button
          type="button"
          className="academic-primary-button"
          disabled={!state.canCreate || editor.saving || deletion.saving}
          onClick={() => editor.open('add')}
        >
          <Plus aria-hidden="true" />
          Add Section
        </button>
      </header>
      <SectionSummary records={state.records} available={state.available} />
      <button
        type="button"
        className="academic-secondary-button"
        onClick={() => (onEnrollment ? onEnrollment() : setEnrollment(true))}
      >
        Manage Student Enrollment
      </button>
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
      {deletion.notice && (
        <p className="section-save-notice" role="status">
          {deletion.notice}
        </p>
      )}
      <SectionTable
        state={state}
        onOpen={editor.open}
        deletionSaving={deletion.saving}
        onDelete={(record) => {
          const stored = state.structure?.records.academic_sections?.find(
            (item) => item.academic_section_id === record.id,
          )
          if (stored) deletion.open(stored)
        }}
      />
      {editor.panel && <SectionDrawer editor={editor} />}
      {deletion.record && <AcademicDeleteDialog deletion={deletion} />}
    </section>
  )
}
