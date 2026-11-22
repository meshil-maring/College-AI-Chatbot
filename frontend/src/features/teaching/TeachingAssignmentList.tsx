import { useState } from 'react'
import type { TeachingAssignment } from '../../types/teaching.ts'
import { Badge, BUTTON_CLASS, statusTone } from '../admin/staff-faculty/StaffFacultyUI.tsx'
import { STATUS_LABEL, assignmentLabel, formatDay, offeringLabel, shownStatus } from './teachingLabels.ts'
import type { TeachingModel } from './useTeaching.ts'

function open(item: TeachingAssignment) {
  return shownStatus(item) === 'active' || item.status === 'pending'
}

function detail(item: TeachingAssignment) {
  const parts = [`From ${formatDay(item.starts_on)}`]
  if (item.planned_end_on) parts.push(`until ${formatDay(item.planned_end_on)}`)
  if (item.ended_at) parts.push(`closed ${formatDay(item.ended_at)}`)
  if (item.decided_by_name && item.needs_approval) {
    parts.push(`${item.status === 'rejected' ? 'rejected' : 'approved'} by ${item.decided_by_name}`)
  }
  if (item.decision_note) parts.push(`“${item.decision_note}”`)
  return parts.join(' · ')
}

/** Current and pending teaching, with closed records on request. */
export default function TeachingAssignmentList({ model }: { model: TeachingModel }) {
  const [history, setHistory] = useState(false)
  const shown = model.assignments.filter((item) => history || open(item))
  const closed = model.assignments.filter((item) => !open(item)).length

  return (
    <section aria-labelledby="teaching-list-heading" className="space-y-3 rounded-xl border border-line bg-surface p-4">
      <div className="flex flex-wrap items-center gap-3">
        <h3 id="teaching-list-heading" className="mr-auto text-sm font-semibold text-content">
          {history ? 'All teaching assignments' : 'Current teaching'}
        </h3>
        {closed > 0 ? (
          <button type="button" onClick={() => setHistory((value) => !value)} className={BUTTON_CLASS}>
            {history ? 'Hide history' : `Show history (${closed})`}
          </button>
        ) : null}
      </div>
      {model.loading ? <p className="text-sm text-muted">Loading…</p> : null}
      {model.loadError ? (
        <p role="alert" className="text-sm text-danger">
          {model.loadError}
        </p>
      ) : null}
      {!model.loading && !model.loadError && shown.length === 0 ? (
        <p className="text-sm text-muted">No teaching assigned yet.</p>
      ) : null}
      {shown.length ? (
        <ul
          aria-label="Teaching assignments"
          className="divide-y divide-line overflow-hidden rounded-lg border border-line"
        >
          {shown.map((item) => {
            const status = shownStatus(item)
            return (
              <li key={item.assignment_id} className="flex flex-wrap items-center gap-3 px-3 py-3">
                <div className="mr-auto flex min-w-0 flex-col">
                  <span className="flex flex-wrap items-center gap-2 text-sm text-content">
                    <span className="font-medium">{item.faculty_name}</span>
                    <Badge tone={statusTone(status)}>{STATUS_LABEL[status]}</Badge>
                    {item.needs_approval ? <Badge tone="info">Cross-department</Badge> : null}
                  </span>
                  <span className="text-sm text-muted">
                    {offeringLabel(item)} · {item.department_name}
                  </span>
                  <span className="text-xs text-muted">{detail(item)}</span>
                </div>
                {item.can_end && open(item) ? (
                  <button
                    type="button"
                    disabled={model.actionKey !== null}
                    aria-label={`${item.status === 'pending' ? 'Withdraw' : 'End'} ${item.faculty_name} teaching ${assignmentLabel(item)}`}
                    onClick={() => void model.end(item)}
                    className={BUTTON_CLASS}
                  >
                    {model.actionKey === `end:${item.assignment_id}`
                      ? 'Saving…'
                      : item.status === 'pending'
                        ? 'Withdraw'
                        : 'End'}
                  </button>
                ) : null}
              </li>
            )
          })}
        </ul>
      ) : null}
    </section>
  )
}
