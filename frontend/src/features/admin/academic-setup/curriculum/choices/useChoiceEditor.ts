import { useState } from 'react'
import type { ChoiceGroup, ChoiceGroupDraft } from '../../../../../types/semesterRegistration.ts'

const emptyDraft = (): ChoiceGroupDraft => ({
  curriculum_version_id: '',
  program_semester_id: '',
  name: '',
  options: [
    { name: 'Option 1', curriculum_subject_ids: [] },
    { name: 'Option 2', curriculum_subject_ids: [] },
  ],
})
export function useChoiceEditor() {
  const [draft, setDraft] = useState(emptyDraft)
  const [editingId, setEditingId] = useState<string>()
  const [validationAttempt, setValidationAttempt] = useState(0)
  function edit(group: ChoiceGroup) {
    setValidationAttempt(0)
    setEditingId(group.choice_group_id)
    setDraft({
      curriculum_version_id: group.curriculum_version_id,
      program_semester_id: group.program_semester_id,
      name: group.name,
      options: group.options.map((option) => ({
        name: option.name,
        curriculum_subject_ids: [...option.curriculum_subject_ids],
      })),
    })
  }
  function reset() {
    setValidationAttempt(0)
    setEditingId(undefined)
    setDraft(emptyDraft())
  }
  function updateOption(index: number, change: Partial<ChoiceGroupDraft['options'][number]>) {
    setDraft((current) => ({
      ...current,
      options: current.options.map((option, item) => (item === index ? { ...option, ...change } : option)),
    }))
  }
  return {
    draft,
    setDraft,
    editingId,
    edit,
    reset,
    updateOption,
    validationAttempt,
    showValidation: () => setValidationAttempt((attempt) => attempt + 1),
  }
}
