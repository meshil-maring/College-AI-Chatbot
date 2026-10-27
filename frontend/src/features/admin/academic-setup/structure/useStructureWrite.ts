import { useEffect, useRef, useState } from 'react'
import { createStructureRecord, updateStructureRecord } from '../../../../services/admin/academicStructure.ts'
import type { StructureCreateMap, StructureEntity, StructureUpdateMap } from '../../../../types/academicStructure.ts'
import type { AcademicStructureState } from './useAcademicStructure.ts'

export function useStructureWrite<E extends StructureEntity>(state: AcademicStructureState, entity: E) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string>()
  const mounted = useRef(true)
  const locked = useRef(false)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])
  async function save(id: string | undefined, payload: StructureCreateMap[E] | StructureUpdateMap[E]) {
    if (!mounted.current || locked.current || !state.canManage(entity)) return false
    locked.current = true
    setSaving(true)
    setError(undefined)
    try {
      const result = id
        ? await updateStructureRecord(state.context.accessToken, entity, id, payload as StructureUpdateMap[E])
        : await createStructureRecord(state.context.accessToken, entity, payload as StructureCreateMap[E])
      const key = `${entity.slice(0, -1)}_id`
      if (result.institution_id !== state.context.institutionId || !(key in result))
        throw new Error('The saved record could not be verified for this institution.')
      if (!mounted.current) return false
      await state.refresh()
      return mounted.current
    } catch (cause) {
      if (mounted.current)
        setError(cause instanceof Error ? cause.message : 'Could not save. Your entries have been kept.')
      return false
    } finally {
      locked.current = false
      if (mounted.current) setSaving(false)
    }
  }
  return { save, saving, error, clearError: () => setError(undefined) }
}
