import type { CurriculumContext } from './useCurriculum.ts'
import type { CurriculumTab } from './curriculumModel.ts'
import VersionedCurriculumPage from './versioning/VersionedCurriculumPage.tsx'
import type { VersionedCurriculumTab } from './versioning/VersionedCurriculumPage.tsx'

export default function CurriculumPage({
  initialTab,
  onOverview,
  activeTab,
  onTabChange,
  ...context
}: CurriculumContext & {
  initialTab?: CurriculumTab
  onOverview: () => void
  activeTab?: VersionedCurriculumTab
  onTabChange?: (tab: VersionedCurriculumTab) => void
}) {
  return (
    <VersionedCurriculumPage
      context={context}
      onOverview={onOverview}
      initialMapping={initialTab === 'mapping'}
      activeTab={activeTab}
      onTabChange={onTabChange}
    />
  )
}
