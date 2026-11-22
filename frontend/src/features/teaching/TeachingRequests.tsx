import { useId, useState } from 'react'
import type { TeachingAssignment } from '../../types/teaching.ts'
import { BUTTON_CLASS, DANGER_BUTTON_CLASS, PRIMARY_BUTTON_CLASS } from '../admin/staff-faculty/StaffFacultyUI.tsx'
import { formatDay, offeringLabel } from './teachingLabels.ts'
import type { TeachingModel } from './useTeaching.ts'

function RequestItem({ item, model }: { item: TeachingAssignment; model: TeachingModel }) {
  const id = useId()
  const [rejecting, setRejecting] = useState(false)
  const [note, setNote] = useState('')
  const busy = model.actionKey !== null
  const deciding = model.actionKey === `decide:${item.assignment_id}`

  async function reject() {
    const failure = await model.decide(item, false, note.trim())
    if (!failure) setRejecting(false)
  }

  return (
    <li className="space-y-2 px-3 py-3">
      <div className="flex flex-col text-sm">
        <span className="font-medium text-content">
          {item.faculty_name} → {offeringLabel(item)}
        </span>
        <span className="text-muted">
          {item.department_name} subject · from {formatDay(item.starts_on)}
          {item.planned_end_on ? ` until ${formatDay(item.planned_end_on)}` : ''} · requested by{' '}
          {item.requested_by_name ?? 'someone'}
        </span>
      </div>
      {rejecting ? (
        <div className="space-y-2">
          <label htmlFor={`${id}-note`} className="text-sm font-medium text-content">
            Reason for rejecting
          </label>
          <textarea
            id={`${id}-note`}
            value={note}
            maxLength={500}
            rows={2}
            onChange={(event) => setNote(event.target.value)}
            className="w-full rounded-lg border border-control bg-surface p-2 text-sm text-content"
          />
          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" disabled={busy} onClick={() => setRejecting(false)} className={BUTTON_CLASS}>
              Cancel
            </button>
            <button
              type="button"
              disabled={busy || !note.trim()}
              onClick={() => void reject()}
              className={DANGER_BUTTON_CLASS}
            >
              {deciding ? 'Rejecting…' : 'Reject request'}
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap justify-end gap-2">
          <button type="button" disabled={busy} onClick={() => setRejecting(true)} className={BUTTON_CLASS}>
            Reject…
          </button>
          <button
            type="button"
            disabled={busy}
            aria-label={`Approve ${item.faculty_name} for ${item.subject_name} (${item.section_code})`}
            onClick={() => void model.decide(item, true, null)}
            className={PRIMARY_BUTTON_CLASS}
          >
            {deciding ? 'Approving…' : 'Approve'}
          </button>
        </div>
      )}
    </li>
  )
}

/** Cross-department requests this viewer may decide. */
export default function TeachingRequests({ model }: { model: TeachingModel }) {
  const waiting = model.assignments.filter((item) => item.can_decide)
  if (waiting.length === 0) return null
  return (
    <section
      aria-labelledby="teaching-requests-heading"
      className="space-y-3 rounded-xl border border-warning bg-surface p-4"
    >
      <h3 id="teaching-requests-heading" className="text-sm font-semibold text-content">
        Requests waiting for you ({waiting.length})
      </h3>
      <p className="text-xs text-muted">
        These teachers are from other departments. Approve to let them teach the subject, or reject with a reason.
      </p>
      <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line">
        {waiting.map((item) => (
          <RequestItem key={item.assignment_id} item={item} model={model} />
        ))}
      </ul>
    </section>
  )
}
