import { useState } from 'react'
import type { AcademicEntity } from '../../../types/academicSetup.ts'
import { ACADEMIC_STAGES, stageForEntity, type AcademicStage } from './academicSetupStages.ts'

export function useAcademicFlow() {
  const [stage, setStage] = useState<AcademicStage>('college')
  const [entity, setEntity] = useState<AcademicEntity>('departments')
  const [busy, setBusy] = useState(false)
  const current = ACADEMIC_STAGES.find((item) => item.key === stage)!
  function navigateEntity(next: AcademicEntity) {
    const destination = stageForEntity(next)
    if (destination) {
      setEntity(next)
      setStage(destination)
    }
  }
  return { stage, setStage, entity, busy, setBusy, current, navigateEntity }
}
