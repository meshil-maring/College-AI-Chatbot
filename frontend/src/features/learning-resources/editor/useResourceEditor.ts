import { useEffect, useRef, useState } from 'react'
import { createResource, saveRevision } from '../../../services/knowledge/resources.ts'
import type { ResourceFields, ResourceRevision } from '../../../types/learningResources.ts'
import type { ResourceContext } from '../data/resourceIdentity.ts'
import type { ResourceActions } from '../data/useResourceActions.ts'
import { draftErrors, resourceDraft, resourcePayload } from './resourceDraft.ts'

export function useResourceEditor(
  context: ResourceContext,
  revision: ResourceRevision | undefined,
  actions: ResourceActions,
  onSaved: (revision: ResourceRevision) => void,
  onDirty: (dirty: boolean) => void,
) {
  const [draft, setDraft] = useState(() => resourceDraft(revision))
  const [errors, setErrors] = useState<ReturnType<typeof draftErrors>>({})
  const baseline = useRef({ draft: JSON.stringify(resourceDraft(revision)), version: revision?.revision_version ?? 0 })
  const dirty = JSON.stringify(draft) !== baseline.current.draft
  useEffect(() => {
    onDirty(dirty)
  }, [dirty, onDirty])
  useEffect(() => {
    // A background read may advance a clean form, but never overwrite typing.
    if (!dirty && revision && revision.revision_version !== baseline.current.version) {
      const next = resourceDraft(revision)
      baseline.current = { draft: JSON.stringify(next), version: revision.revision_version }
      setDraft(next)
    }
  }, [dirty, revision])
  function change<K extends keyof ResourceFields>(field: K, value: ResourceFields[K]) {
    setDraft((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: undefined }))
  }
  async function save() {
    const invalid = draftErrors(draft)
    setErrors(invalid)
    if (Object.keys(invalid).length) return
    const payload = resourcePayload(draft)
    const saved = await actions.run(() =>
      revision
        ? saveRevision(context.accessToken, revision, payload, baseline.current.version)
        : createResource(context.accessToken, payload),
    )
    if (!saved) return
    const next = resourceDraft(saved)
    baseline.current = { draft: JSON.stringify(next), version: saved.revision_version }
    setDraft(next)
    onDirty(false)
    onSaved(saved)
  }
  return { draft, errors, dirty, change, save }
}
