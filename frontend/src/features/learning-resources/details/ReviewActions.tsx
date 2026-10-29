import { useEffect, useRef, useState } from 'react'
import { decideRevision } from '../../../services/knowledge/resources.ts'
import type { ResourceRevision, ReviewAction } from '../../../types/learningResources.ts'
import type { ResourceContext } from '../data/resourceIdentity.ts'
import type { ResourceActions } from '../data/useResourceActions.ts'
import { audienceLabel, isReady } from '../resourcePresentation.ts'
import { canEditRevision } from '../data/resourceIdentity.ts'

const labels: Record<ReviewAction, string> = {
  submit: 'Submit for review',
  request_changes: 'Request changes',
  approve: 'Approve revision',
  publish: 'Publish revision',
  unpublish: 'Unpublish resource',
}
export default function ReviewActions({
  context,
  revision,
  actions,
  disabled,
  onDirty,
}: {
  context: ResourceContext
  revision: ResourceRevision
  actions: ResourceActions
  disabled: boolean
  onDirty: (dirty: boolean) => void
}) {
  const [notes, setNotes] = useState('')
  const [confirm, setConfirm] = useState<ReviewAction | null>(null)
  const cancel = useRef<HTMLButtonElement>(null)
  const status = revision.lifecycle_status
  const audienceValid = revision.visibility !== 'restricted' || revision.audience_roles.length > 0
  const submit = canEditRevision(context, revision)
  const review = context.canDecide && ['under_review', 'approved'].includes(status)
  const unpublish = context.canDecide && status === 'published'
  const busy = disabled || actions.saving || actions.blocked
  useEffect(() => {
    onDirty(Boolean(notes.trim()))
  }, [notes, onDirty])
  useEffect(() => {
    if (confirm) cancel.current?.focus()
  }, [confirm])
  async function decide(action: ReviewAction) {
    if (busy || (action === 'request_changes' && !notes.trim())) return
    const saved = await actions.run(() => decideRevision(context.accessToken, revision, action, notes), 'review')
    if (saved) {
      setConfirm(null)
      setNotes('')
      onDirty(false)
    }
  }
  if (!submit && !review && !unpublish) return null
  return (
    <section className="lr-review-actions" aria-label="Review actions">
      <h3>{submit ? 'Send for admin review' : 'Publication and review'}</h3>
      {submit && (
        <p className="lr-help">
          Choose an audience and index every file before submitting. Only admins can approve and publish.
        </p>
      )}
      {review && (
        <>
          <label htmlFor="resource-review-notes">Review feedback</label>
          <textarea
            id="resource-review-notes"
            value={notes}
            maxLength={5000}
            disabled={busy || Boolean(confirm)}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Required when requesting changes; optional for approval."
          />
        </>
      )}
      {confirm ? (
        <div className="lr-confirm" role="group" aria-label="Confirm resource decision">
          <h4>{labels[confirm]}?</h4>
          <p>
            <strong>{revision.title}</strong> · Revision {revision.revision_number}
          </p>
          <p>
            Audience: <strong>{audienceLabel(revision)}</strong>
          </p>
          <p className="lr-help">
            {confirm === 'unpublish'
              ? 'This removes the resource from future chatbot answers and reader access.'
              : confirm === 'publish'
                ? 'These exact indexed files and the selected audience will become the live resource.'
                : confirm === 'request_changes'
                  ? 'The revision returns to draft with your feedback.'
                  : 'The exact files and audience shown above will be recorded for this decision.'}
          </p>
          <div className="lr-actions">
            <button
              ref={cancel}
              type="button"
              className="lr-secondary"
              disabled={actions.saving}
              onClick={() => setConfirm(null)}
            >
              Cancel decision
            </button>
            <button
              type="button"
              className={confirm === 'unpublish' ? 'lr-danger-button' : 'ui-primary'}
              disabled={busy}
              onClick={() => void decide(confirm)}
            >
              {actions.saving ? 'Saving…' : `Confirm ${labels[confirm].toLowerCase()}`}
            </button>
          </div>
        </div>
      ) : (
        <div className="lr-actions">
          {submit && (
            <button
              type="button"
              className="ui-primary"
              disabled={busy || !audienceValid || !isReady(revision)}
              onClick={() => setConfirm('submit')}
            >
              {labels.submit}
            </button>
          )}
          {review && (
            <button
              type="button"
              className="lr-secondary"
              disabled={busy || !notes.trim()}
              onClick={() => setConfirm('request_changes')}
            >
              {labels.request_changes}
            </button>
          )}
          {review && (
            <button
              type="button"
              className="ui-primary"
              disabled={busy}
              onClick={() => setConfirm(status === 'approved' ? 'publish' : 'approve')}
            >
              {status === 'approved' ? labels.publish : labels.approve}
            </button>
          )}
          {unpublish && (
            <button type="button" className="lr-danger-button" disabled={busy} onClick={() => setConfirm('unpublish')}>
              {labels.unpublish}
            </button>
          )}
        </div>
      )}
      {disabled && (
        <p className="lr-help">
          Save your detail changes and upload any selected file before making a review decision.
        </p>
      )}
    </section>
  )
}
