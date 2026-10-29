import type { LearningResource, ResourceFields } from '../../../types/learningResources.ts'

export function resourceDraft(resource?: LearningResource): ResourceFields {
  return {
    title: resource?.title ?? '',
    description: resource?.description ?? '',
    source_type: resource?.source_type ?? 'handbook',
    audience: {
      mode:
        resource?.visibility === 'public'
          ? 'public'
          : resource?.visibility === 'authenticated'
            ? 'institution'
            : 'roles',
      roles: [...(resource?.audience_roles ?? [])],
    },
    effective_from: resource?.effective_from ?? '',
    effective_until: resource?.effective_until ?? '',
  }
}
export function draftErrors(draft: ResourceFields) {
  const errors: Partial<Record<keyof ResourceFields, string>> = {}
  if (!draft.title.trim()) errors.title = 'Enter a resource title.'
  if (!draft.source_type.trim() || ['faq', 'notice'].includes(draft.source_type))
    errors.source_type = 'Choose a file resource type.'
  if (draft.effective_from && draft.effective_until && draft.effective_until < draft.effective_from)
    errors.effective_until = 'Choose an end date on or after the start date.'
  return errors
}
export function resourcePayload(draft: ResourceFields): ResourceFields {
  return {
    ...draft,
    title: draft.title.trim(),
    description: draft.description?.trim() || null,
    effective_from: draft.effective_from || null,
    effective_until: draft.effective_until || null,
  }
}
