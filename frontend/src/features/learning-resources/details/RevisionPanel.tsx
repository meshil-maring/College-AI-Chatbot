import { useEffect, useState } from 'react'
import type { ResourceRevision } from '../../../types/learningResources.ts'
import type { ResourceContext } from '../data/resourceIdentity.ts'
import { canEditRevision, canCloneResource } from '../data/resourceIdentity.ts'
import type { ResourceActions } from '../data/useResourceActions.ts'
import { createRevision } from '../../../services/knowledge/resources.ts'
import ResourceEditor from '../editor/ResourceEditor.tsx'
import ResourceUploads from '../editor/ResourceUploads.tsx'
import ResourceFiles from './ResourceFiles.tsx'
import ResourceInformation from './ResourceInformation.tsx'
import ReviewActions from './ReviewActions.tsx'
import { RevisionBadge } from '../ResourceBadges.tsx'

export default function RevisionPanel({
  context,
  revision,
  actions,
  disabled,
  onOpen,
  onDirty,
}: {
  context: ResourceContext
  revision: ResourceRevision
  actions: ResourceActions
  disabled: boolean
  onOpen: (revision: ResourceRevision) => void
  onDirty: (dirty: boolean) => void
}) {
  const [metadataDirty, setMetadataDirty] = useState(false)
  const [fileDirty, setFileDirty] = useState(false)
  const [notesDirty, setNotesDirty] = useState(false)
  const edit = canEditRevision(context, revision)
  useEffect(() => {
    onDirty(metadataDirty || fileDirty || notesDirty)
  }, [metadataDirty, fileDirty, notesDirty, onDirty])
  return (
    <>
      <div className="lr-revision-summary">
        <RevisionBadge status={revision.lifecycle_status} />
        <span>Revision {revision.revision_number}</span>
      </div>
      {revision.review_notes && (
        <section className="lr-callout lr-warning" aria-label="Reviewer feedback">
          <h3>Reviewer feedback</h3>
          <p>{revision.review_notes}</p>
        </section>
      )}
      {edit ? (
        <ResourceEditor
          context={context}
          revision={revision}
          actions={actions}
          disabled={disabled || fileDirty}
          onSaved={() => undefined}
          onDirty={setMetadataDirty}
        />
      ) : (
        <ResourceInformation resource={revision} />
      )}
      {edit ? (
        <ResourceUploads
          context={context}
          revision={revision}
          actions={actions}
          disabled={disabled || metadataDirty}
          onDirty={setFileDirty}
        />
      ) : (
        <ResourceFiles files={revision.documents} />
      )}
      {!edit && ['under_review', 'approved'].includes(revision.lifecycle_status) && (
        <p className="lr-callout lr-info">
          This revision is frozen for review. Its files and audience cannot be edited until an admin requests changes.
        </p>
      )}
      <ReviewActions
        context={context}
        revision={revision}
        actions={actions}
        disabled={disabled || metadataDirty || fileDirty}
        onDirty={setNotesDirty}
      />
      {revision.lifecycle_status === 'published' && canCloneResource(context, revision) && (
        <div className="lr-form-footer">
          <p className="lr-help">Updates start a new draft. The live resource stays available during review.</p>
          <button
            type="button"
            className="lr-secondary"
            disabled={disabled || actions.saving || actions.blocked}
            onClick={() =>
              void actions
                .run(() => createRevision(context.accessToken, revision.knowledge_source_id))
                .then((saved) => {
                  if (saved) onOpen(saved)
                })
            }
          >
            Create new revision
          </button>
        </div>
      )}
    </>
  )
}
