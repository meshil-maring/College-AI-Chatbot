import { useEffect, useRef, useState } from 'react'
import { useApiMutation } from '../../../../hooks/useApiQuery.ts'
import {
  deleteDepartment,
  deleteProgram,
  deleteAcademicYear,
  deleteSemester,
} from '../../../../services/admin/academics.ts'
import { deleteAcademicSection } from '../../../../services/admin/academicStructure.ts'
import type { AcademicCatalogue } from '../../../../types/academicSetup.ts'
import type { StructureCatalogue } from '../../../../types/academicStructure.ts'
import {
  deletionBlocker,
  deletionConfig,
  deletionId,
  deletionRecords,
  type DeletionEntity,
  type DeletionRecord,
} from './academicDeletionModel.ts'

const deleteRequests = {
  departments: deleteDepartment,
  programs: deleteProgram,
  academic_years: deleteAcademicYear,
  semesters: deleteSemester,
  academic_sections: deleteAcademicSection,
}

interface Options {
  entity: DeletionEntity
  accessToken: string
  institutionId: string
  catalogue?: AcademicCatalogue
  structure?: StructureCatalogue
  busy: boolean
  refresh: () => Promise<unknown>
}

export function useAcademicDeletion({
  entity,
  accessToken,
  institutionId,
  catalogue,
  structure,
  busy,
  refresh,
}: Options) {
  const { label, focusTarget } = deletionConfig[entity]
  const noun = label.toLowerCase()
  const [record, setRecord] = useState<DeletionRecord | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const mounted = useRef(true)
  const submitting = useRef(false)
  const source = entity === 'academic_sections' ? structure : catalogue
  const records = deletionRecords(entity, catalogue, structure)
  const canManage = Boolean(
    source?.institution_id === institutionId && records && source.manageable.some((item) => item === entity) && !busy,
  )
  const latest = record && records?.find((item) => deletionId(entity, item) === deletionId(entity, record))
  const blocked = deletionBlocker(entity, latest || record, catalogue, structure)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const mutation = useApiMutation<DeletionRecord, DeletionRecord>({
    mutationFn: async (selected) => {
      if (!mounted.current || !canManage || blocked)
        throw new Error(`${label} deletion is unavailable. Refresh and review its connections.`)
      const id = deletionId(entity, selected)
      if (
        !id ||
        selected.institution_id !== institutionId ||
        !records?.some((item) => deletionId(entity, item) === id && item.institution_id === institutionId)
      )
        throw new Error(`This ${noun} is no longer available.`)
      const deleted = await deleteRequests[entity](accessToken, id)
      if (deleted.institution_id !== institutionId || deletionId(entity, deleted) !== id)
        throw new Error(`The ${noun} deletion response could not be verified. Refresh the list.`)
      return deleted
    },
    onSuccess: async () => {
      if (!mounted.current) return
      setRecord(null)
      setNotice(`${label} deleted successfully.`)
      await refresh()
    },
    onError: (cause) => {
      if (!mounted.current) return
      setError(cause instanceof Error ? cause.message : `Could not delete ${noun}. Try again.`)
    },
    onSettled: () => {
      submitting.current = false
    },
  })

  return {
    entity,
    label,
    noun,
    focusTarget,
    canManage,
    record,
    error,
    notice,
    clearNotice: () => setNotice(null),
    blocked,
    canDelete: canManage && !blocked,
    saving: mutation.isPending,
    open: (selected: DeletionRecord) => {
      if (!canManage || mutation.isPending || selected.institution_id !== institutionId) return
      setRecord(selected)
      setError(null)
      setNotice(null)
    },
    close: () => {
      if (!mutation.isPending && !submitting.current) setRecord(null)
    },
    confirm: () => {
      if (!record || !canManage || blocked || mutation.isPending || submitting.current) return
      submitting.current = true
      setError(null)
      mutation.mutate(record)
    },
  }
}

export type AcademicDeletion = ReturnType<typeof useAcademicDeletion>
