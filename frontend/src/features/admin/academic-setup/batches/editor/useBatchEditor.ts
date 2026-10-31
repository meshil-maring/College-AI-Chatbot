import { useRef, useState } from 'react'
import {
  batchDraft,
  emptyBatch,
  validateBatch,
  type BatchDraft,
  type BatchRecord,
  type BatchStatus,
} from '../batchModel.ts'
import type { BatchesState } from '../useBatches.ts'

export function useBatchEditor(state: BatchesState, onCreated?: () => void) {
  const [panel, setPanel] = useState<{ mode: 'add' | 'view' | 'edit'; record?: BatchRecord }>()
  const [draft, setDraft] = useState(emptyBatch)
  const [confirmation, setConfirmation] = useState<'discard' | 'status'>()
  const [error, setError] = useState<string>()
  const initial = useRef(JSON.stringify(emptyBatch()))
  function open(mode: 'add' | 'view' | 'edit', record?: BatchRecord, status?: BatchStatus) {
    if (state.write.saving || (mode !== 'view' && !state.canManage)) return
    const next = record ? batchDraft(record) : emptyBatch()
    initial.current = JSON.stringify(next)
    setDraft(status ? { ...next, status } : next)
    setError(undefined)
    setConfirmation(undefined)
    setPanel({ mode, record })
  }
  function change<K extends keyof BatchDraft>(field: K, value: BatchDraft[K]) {
    if (state.write.saving) return
    state.write.clearError()
    setDraft((current) => {
      const next = { ...current, [field]: value }
      if (field === 'programId' && value !== current.programId) next.curriculumId = ''
      return next
    })
    setError(undefined)
  }
  function close() {
    if (state.write.saving) return
    if (panel?.mode !== 'view' && JSON.stringify(draft) !== initial.current) setConfirmation('discard')
    else setPanel(undefined)
  }
  async function commit() {
    const saved = await state.save(
      {
        ...draft,
        name: draft.name.trim(),
        code: draft.code.trim(),
        description: draft.description.trim(),
        id: panel?.record?.id ?? '',
        studentCount: panel?.record?.studentCount ?? null,
      },
      Boolean(panel?.record),
    )
    if (!saved) return
    if (!panel?.record) onCreated?.()
    setPanel(undefined)
    setConfirmation(undefined)
  }
  function submit() {
    if (!panel || panel.mode === 'view' || state.write.saving || !state.canManage) return
    const issue = validateBatch(draft, state.records, state.programs, state.curricula, panel.record?.id)
    if (issue) {
      setError(issue)
      return
    }
    if (panel.record && draft.status !== panel.record.status) setConfirmation('status')
    else void commit()
  }
  return {
    panel,
    draft,
    confirmation,
    error: error ?? state.write.error,
    saving: state.write.saving,
    state,
    open,
    change,
    close,
    submit,
    keepEditing: () => {
      if (!state.write.saving) setConfirmation(undefined)
    },
    confirm: () => {
      if (state.write.saving) return
      if (confirmation === 'status') void commit()
      else {
        setPanel(undefined)
        setConfirmation(undefined)
      }
    },
  }
}
export type BatchEditor = ReturnType<typeof useBatchEditor>
