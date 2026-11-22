import { useState } from 'react'
import type { MemberResponsibility } from '../../../../types/admin/responsibilities.ts'
import { Badge, BUTTON_CLASS } from '../StaffFacultyUI.tsx'
import { RESPONSIBILITY_LABELS } from './AssignResponsibilityForm.tsx'
import type { MemberResponsibilitiesModel } from './useMemberResponsibilities.ts'

function formatDate(value: string | null) {
  if (!value) return ''
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString(undefined, {
    dateStyle: 'medium',
    timeZone: 'UTC',
  })
}

function term(item: MemberResponsibility) {
  const from = `From ${formatDate(item.starts_on)}`
  if (item.ended_at) return `${from} · ended ${formatDate(item.ended_at)}`
  if (item.planned_end_on)
    return `${from} · ${item.is_current ? 'until' : 'ran out after'} ${formatDate(item.planned_end_on)}`
  return from
}

/** Current Class In-Charge and Subject Coordinator appointments, with history on request. */
export default function ResponsibilityList({ model }: { model: MemberResponsibilitiesModel }) {
  const [history, setHistory] = useState(false)
  const shown = model.responsibilities.filter((item) => history || item.is_current)
  const past = model.responsibilities.length - model.responsibilities.filter((item) => item.is_current).length

  return (
    <section
      aria-labelledby="responsibility-list-heading"
      className="space-y-3 rounded-xl border border-line bg-surface p-4"
    >
      <div className="flex flex-wrap items-center gap-3">
        <h3 id="responsibility-list-heading" className="mr-auto text-sm font-semibold text-content">
          {history ? 'All appointments' : 'Current appointments'}
        </h3>
        {past > 0 ? (
          <button type="button" onClick={() => setHistory((value) => !value)} className={BUTTON_CLASS}>
            {history ? 'Hide history' : `Show history (${past})`}
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
        <p className="text-sm text-muted">No Class In-Charge or Subject Coordinator appointed yet.</p>
      ) : null}
      {shown.length ? (
        <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line">
          {shown.map((item) => (
            <li key={item.responsibility_id} className="flex flex-wrap items-center gap-3 px-3 py-3">
              <div className="mr-auto flex min-w-0 flex-col">
                <span className="flex flex-wrap items-center gap-2 text-sm text-content">
                  <span className="font-medium">{item.faculty_name}</span>
                  <Badge tone={item.is_current ? 'info' : 'neutral'}>
                    {RESPONSIBILITY_LABELS[item.responsibility]}
                  </Badge>
                  {item.is_current ? null : <Badge tone="neutral">Ended</Badge>}
                </span>
                <span className="text-sm text-muted">
                  {item.target_name ?? 'Removed item'}
                  {item.target_code ? ` (${item.target_code})` : ''}
                </span>
                <span className="text-xs text-muted">{term(item)}</span>
              </div>
              {item.is_current ? (
                <button
                  type="button"
                  disabled={model.actionKey !== null}
                  aria-label={`End ${item.faculty_name} as ${RESPONSIBILITY_LABELS[item.responsibility]} of ${item.target_name ?? 'this item'}`}
                  onClick={() => void model.end(item)}
                  className={BUTTON_CLASS}
                >
                  {model.actionKey === `end:${item.responsibility_id}` ? 'Ending…' : 'End'}
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
