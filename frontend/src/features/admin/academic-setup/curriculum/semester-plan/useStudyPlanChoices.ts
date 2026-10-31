import { useCallback, useState } from 'react'
import type { StructureContext } from '../../structure/useAcademicStructure.ts'
import { useRegistrationAdmin } from '../../registration/useRegistrationAdmin.ts'

export function useStudyPlanChoices(context: StructureContext) {
  const state = useRegistrationAdmin(context)
  const [drafts, setDrafts] = useState<ReadonlySet<string>>(() => new Set())
  const trackDraft = useCallback((id: string, open: boolean) => {
    setDrafts((current) => {
      if (current.has(id) === open) return current
      const next = new Set(current)
      if (open) next.add(id)
      else next.delete(id)
      return next
    })
  }, [])
  return { ...state, hasDrafts: drafts.size > 0, trackDraft }
}
export type StudyPlanChoicesState = ReturnType<typeof useStudyPlanChoices>
