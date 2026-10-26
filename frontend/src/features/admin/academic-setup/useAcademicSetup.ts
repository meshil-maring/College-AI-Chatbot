import { useEffect, useRef, useState } from 'react'
import { useApiMutation, useApiQuery } from '../../../hooks/useApiQuery.ts'
import { createAcademicRecord, getAcademicSetup, updateAcademicRecord } from '../../../services/admin/academics.ts'
import type { AcademicEntity, AcademicRecord } from '../../../types/academicSetup.ts'
import {
  ACADEMIC_ENTITIES,
  ACADEMIC_SINGULAR,
  academicDraftError,
  academicPayload,
  academicRecordId,
  academicUpdatePayload,
  makeAcademicDraft,
} from './academicSetupForm.ts'

export function useAcademicSetup(accessToken: string, identity: string) {
  const query = useApiQuery(['admin', 'academic-setup', identity], () => getAcademicSetup(accessToken))
  const [selected, setSelected] = useState<AcademicEntity>('departments')
  const [editing, setEditing] = useState<AcademicRecord | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [draft, setDraft] = useState(makeAcademicDraft)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const entities = ACADEMIC_ENTITIES.filter((entity) => query.data?.records[entity] !== undefined)
  const entity = entities.includes(selected) ? selected : (entities[0] ?? 'departments')
  const manageable = query.data?.manageable.includes(entity) ?? false
  const records: AcademicRecord[] = (query.data?.records[entity] ?? []).filter(
    (record) => record.institution_id === query.data?.institution_id,
  )
  const mutation = useApiMutation<AcademicRecord, { record?: AcademicRecord; toggle?: boolean }>({
    mutationFn: async ({ record, toggle }) => {
      if (!manageable) throw new Error('You have read-only access to this catalogue.')
      if (toggle && record) {
        const payload =
          record.is_active && 'is_current' in record
            ? { is_active: false, is_current: false }
            : { is_active: !record.is_active }
        return updateAcademicRecord(accessToken, entity, academicRecordId(record), payload)
      }
      const payload = academicPayload(entity, draft)
      if (record) {
        return updateAcademicRecord(accessToken, entity, academicRecordId(record), academicUpdatePayload(entity, draft))
      }
      return createAcademicRecord(accessToken, entity, payload)
    },
    onSuccess: async () => {
      if (!mounted.current) return
      setFormOpen(false)
      setEditing(null)
      setDraft(makeAcademicDraft())
      setNotice('Saved successfully.')
      await query.refetch()
    },
    onError: (cause) => {
      if (mounted.current) setError(cause instanceof Error ? cause.message : 'Could not save this record.')
    },
  })

  function select(next: AcademicEntity) {
    if (mutation.isPending) return
    setSelected(next)
    setFormOpen(false)
    setEditing(null)
    setDraft(makeAcademicDraft())
    setError(null)
    setNotice(null)
  }

  function open(record?: AcademicRecord) {
    setEditing(record ?? null)
    setDraft(makeAcademicDraft(record))
    setError(null)
    setNotice(null)
    setFormOpen(true)
  }

  function save() {
    if (mutation.isPending) return
    const validation = academicDraftError(entity, draft)
    setError(validation)
    setNotice(null)
    if (!validation) mutation.mutate({ record: editing ?? undefined })
  }

  function toggle(record: AcademicRecord) {
    if (mutation.isPending) return
    setError(null)
    setNotice(null)
    mutation.mutate({ record, toggle: true })
  }

  return {
    query,
    entities,
    entity,
    records,
    manageable,
    editing,
    formOpen,
    draft,
    setDraft,
    error,
    notice,
    busy: mutation.isPending || query.isFetching || query.isError,
    select,
    open,
    save,
    toggle,
    close: () => {
      if (!mutation.isPending) {
        setFormOpen(false)
        setError(null)
      }
    },
    singular: ACADEMIC_SINGULAR[entity],
  }
}
