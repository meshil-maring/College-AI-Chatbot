import type { CurriculumContext } from './useCurriculum.ts'
import type { CurriculumTab } from './curriculumModel.ts'
import VersionedCurriculumPage from './versioning/VersionedCurriculumPage.tsx'

export default function CurriculumPage({
  initialTab,
  onOverview,
  ...context
}: CurriculumContext & { initialTab?: CurriculumTab; onOverview: () => void }) {
  return <VersionedCurriculumPage context={context} onOverview={onOverview} initialMapping={initialTab === 'mapping'} />
}
