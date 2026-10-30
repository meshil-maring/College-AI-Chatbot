import type { ChoiceGroupDraft } from '../../../../../types/semesterRegistration.ts'

export function choiceValidation(draft: ChoiceGroupDraft, availableSubjectIds: ReadonlySet<string>): string[] {
  const issues: string[] = []
  if (!draft.curriculum_version_id) issues.push('Select a draft curriculum.')
  if (!draft.program_semester_id) issues.push('Select a program semester.')
  if (!draft.name.trim()) issues.push('Enter a group name.')
  if (draft.options.length < 2) issues.push('Add at least two options.')
  if (new Set(draft.options.map((option) => option.name.trim().toLowerCase())).size !== draft.options.length)
    issues.push('Give each option a different name.')
  draft.options.forEach((option, index) => {
    const name = option.name.trim() || `Option ${index + 1}`
    if (!option.name.trim()) issues.push(`Enter a name for Option ${index + 1}.`)
    if (!option.curriculum_subject_ids.length) issues.push(`Select at least one subject for ${name}.`)
    else if (option.curriculum_subject_ids.some((id) => !availableSubjectIds.has(id)))
      issues.push(`Review ${name}: a selected subject is no longer available as an optional mapping.`)
  })
  return issues
}
