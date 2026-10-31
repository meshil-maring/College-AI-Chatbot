import { useState } from 'react'
import type { StructureContext } from '../../structure/useAcademicStructure.ts'
import { useAcademicStructure } from '../../structure/useAcademicStructure.ts'
import StructureRecordsPage from '../../structure/StructureRecordsPage.tsx'
import CurriculumTabs from '../CurriculumTabs.tsx'
import { ExistingCurriculumMappings } from '../ExistingCurriculumMappings.tsx'
import SemesterPlanPage from '../semester-plan/SemesterPlanPage.tsx'
import StudyPlanSteps from '../semester-plan/StudyPlanSteps.tsx'
import '../semester-plan/study-plan.css'

// Previously saved option destinations now use the combined semester view.
export type VersionedCurriculumTab = 'versions' | 'subjects' | 'options' | 'history' | 'existing'
type Tab = VersionedCurriculumTab
const tabs: { id: Tab; label: string }[] = [
  { id: 'versions', label: 'Curriculum List' },
  { id: 'subjects', label: 'Subjects by semester' },
  { id: 'history', label: 'Version History' },
  { id: 'existing', label: 'Existing Program Mappings' },
]
export default function VersionedCurriculumPage({
  context,
  onOverview,
  initialMapping = false,
  activeTab,
  onTabChange,
  onBatches,
}: {
  context: StructureContext
  onOverview: () => void
  initialMapping?: boolean
  activeTab?: Tab
  onTabChange?: (tab: Tab) => void
  onBatches?: () => void
}) {
  const state = useAcademicStructure(context)
  const [localTab, setLocalTab] = useState<Tab>(initialMapping ? 'subjects' : 'versions')
  const requestedTab = activeTab ?? localTab
  const tab = requestedTab === 'options' ? 'subjects' : requestedTab
  const setTab = onTabChange ?? setLocalTab
  const [versionId, setVersionId] = useState('')
  const versions = state.structure?.records.curriculum_versions ?? []
  const navigation = (
    <CurriculumTabs items={tabs} value={tab} onChange={setTab} prefix="versioned-curriculum" label="Curriculum views" />
  )
  if (tab === 'subjects')
    return (
      <SemesterPlanPage
        state={state}
        versionId={versionId}
        onVersionChange={setVersionId}
        onOverview={onOverview}
        onCreateCurriculum={() => setTab('versions')}
        onBatches={onBatches}
        navigation={navigation}
      />
    )
  if (tab === 'existing')
    return (
      <>
        {navigation}
        <ExistingCurriculumMappings {...context} onOverview={onOverview} />
      </>
    )
  return (
    <StructureRecordsPage
      key={tab}
      context={context}
      entity="curriculum_versions"
      title="Curriculum"
      onOverview={onOverview}
    >
      {navigation}
      {tab === 'versions' && (
        <>
          <StudyPlanSteps />
          <button type="button" className="academic-secondary-button" onClick={() => setTab('subjects')}>
            Choose subjects by semester
          </button>
        </>
      )}
      {tab === 'history' && (
        <section aria-label="Published curriculum history">
          <p>Published and archived versions retain their original subject mappings and batch assignments.</p>
          <ul>
            {versions
              .filter((version) => version.published_at)
              .map((version) => (
                <li key={version.curriculum_version_id}>
                  {version.name} · v{version.version} · Published{' '}
                  {new Date(version.published_at!).toLocaleDateString('en-IN')} · {version.status}
                </li>
              ))}
          </ul>
          {!versions.some((version) => version.published_at) && <p>No published versions yet.</p>}
        </section>
      )}
    </StructureRecordsPage>
  )
}
