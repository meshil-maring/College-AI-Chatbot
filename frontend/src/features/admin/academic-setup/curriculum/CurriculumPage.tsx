import type { StructureContext } from '../structure/useAcademicStructure.ts'
import VersionedCurriculumPage from './versioning/VersionedCurriculumPage.tsx'
import type { VersionedCurriculumTab } from './versioning/VersionedCurriculumPage.tsx'

export default function CurriculumPage({
  onOverview,
  activeTab,
  onTabChange,
  onBatches,
  ...context
}: StructureContext & {
  onOverview: () => void
  activeTab?: VersionedCurriculumTab
  onTabChange?: (tab: VersionedCurriculumTab) => void
  onBatches?: () => void
}) {
  return (
    <VersionedCurriculumPage
      context={context}
      onOverview={onOverview}
      activeTab={activeTab}
      onTabChange={onTabChange}
      onBatches={onBatches}
    />
  )
}
