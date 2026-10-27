import { useState } from 'react'
import type { StructureContext } from '../../structure/useAcademicStructure.ts'
import { useAcademicStructure } from '../../structure/useAcademicStructure.ts'
import StructureRecordsPage from '../../structure/StructureRecordsPage.tsx'
import CurriculumTabs from '../CurriculumTabs.tsx'
import { ExistingCurriculumMappings } from '../ExistingCurriculumMappings.tsx'

type Tab = 'versions' | 'subjects' | 'history' | 'existing'
const tabs: { id: Tab; label: string }[] = [
  { id: 'versions', label: 'Curriculum List' },
  { id: 'subjects', label: 'Subject Mapping' },
  { id: 'history', label: 'Version History' },
  { id: 'existing', label: 'Existing Program Mappings' },
]
export default function VersionedCurriculumPage({
  context,
  onOverview,
  initialMapping = false,
}: {
  context: StructureContext
  onOverview: () => void
  initialMapping?: boolean
}) {
  const state = useAcademicStructure(context)
  const [tab, setTab] = useState<Tab>(initialMapping ? 'subjects' : 'versions')
  const [versionId, setVersionId] = useState('')
  const versions = state.structure?.records.curriculum_versions ?? []
  const navigation = (
    <CurriculumTabs items={tabs} value={tab} onChange={setTab} prefix="versioned-curriculum" label="Curriculum views" />
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
      entity={tab === 'subjects' ? 'curriculum_subjects' : 'curriculum_versions'}
      title="Curriculum"
      onOverview={onOverview}
      defaults={versionId ? { curriculum_version_id: versionId } : {}}
      filter={
        tab === 'subjects' && versionId
          ? (row) => 'curriculum_version_id' in row && row.curriculum_version_id === versionId
          : undefined
      }
    >
      {navigation}
      {tab === 'subjects' && (
        <label className="structure-field">
          Curriculum Version
          <select value={versionId} onChange={(event) => setVersionId(event.target.value)}>
            <option value="">All curriculum versions</option>
            {versions.map((version) => (
              <option key={version.curriculum_version_id} value={version.curriculum_version_id}>
                {version.name} · v{version.version} ({version.status})
              </option>
            ))}
          </select>
        </label>
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
