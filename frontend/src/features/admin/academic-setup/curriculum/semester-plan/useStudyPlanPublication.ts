import { useState } from 'react'
import type { CurriculumVersion } from '../../../../../types/academicStructure.ts'
import type { AcademicStructureState } from '../../structure/useAcademicStructure.ts'
import { useStructureWrite } from '../../structure/useStructureWrite.ts'
import { studyPlanCanChange, studyPlanSemesters } from './studyPlanModel.ts'
import type { StudyPlanChoicesState } from './useStudyPlanChoices.ts'

export function useStudyPlanPublication(
  state: AcademicStructureState,
  version: CurriculumVersion,
  choices: StudyPlanChoicesState,
) {
  const [reviewing, setReviewing] = useState(false)
  const [notice, setNotice] = useState('')
  const write = useStructureWrite(state, 'curriculum_versions')
  const semesters = studyPlanSemesters(state, version)
  const count = semesters.reduce(
    (total, item) => total + item.subjects.filter((subject) => subject.is_active).length,
    0,
  )
  const emptySemesters = semesters.filter(
    (item) => item.semester && !item.subjects.some((subject) => subject.is_active),
  )
  const unconfiguredSemesters = semesters.filter((item) => !item.semester)
  const canPublish =
    state.canManage('curriculum_versions') &&
    studyPlanCanChange(state, version) &&
    count > 0 &&
    !choices.busy &&
    !choices.hasDrafts
  async function publish() {
    if (!reviewing || !canPublish) return
    if (await write.save(version.curriculum_version_id, { status: 'published' })) {
      setReviewing(false)
      setNotice('Study plan published. You can now assign it to a batch.')
    }
  }
  return {
    reviewing,
    notice,
    semesters,
    count,
    emptySemesters: emptySemesters.length,
    unconfiguredSemesters: unconfiguredSemesters.length,
    semesterCount: semesters.length,
    canPublish,
    saving: write.saving,
    error: write.error,
    publish,
    review: () => {
      if (!canPublish || write.saving) return
      write.clearError()
      setReviewing(true)
    },
    close: () => {
      if (!write.saving) setReviewing(false)
    },
  }
}
