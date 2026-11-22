import { useId, useState, type FormEvent } from 'react'
import { PRIMARY_BUTTON_CLASS, SELECT_CLASS } from '../admin/staff-faculty/StaffFacultyUI.tsx'
import { assignmentOutcome, offeringLabel, todayIso } from './teachingLabels.ts'
import type { TeachingModel } from './useTeaching.ts'

const LABEL = 'flex flex-col gap-1 text-sm font-medium text-content'

/** Choose a Faculty member and a subject offering; the form says whether approval is needed. */
export default function AssignTeachingForm({ model }: { model: TeachingModel }) {
  const id = useId()
  const [facultyId, setFacultyId] = useState('')
  const [offeringId, setOfferingId] = useState('')
  const [startsOn, setStartsOn] = useState(todayIso())
  const [plannedEnd, setPlannedEnd] = useState('')
  const isAdmin = model.data?.is_admin ?? false
  const heads = model.data?.head_department_ids ?? []
  const teacher = model.faculty.find((item) => item.user_id === facultyId)
  const offering = model.offerings.find((item) => item.academic_offering_id === offeringId)
  const outcome = teacher && offering ? assignmentOutcome(offering, teacher, isAdmin, heads) : null
  const datesWrong = Boolean(plannedEnd) && (plannedEnd < startsOn || plannedEnd < todayIso())
  const sending = model.actionKey === 'assign'
  const blocked = !teacher || !offering || !startsOn || datesWrong || outcome === 'refused'

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (blocked) return
    const failure = await model.assign({
      academic_offering_id: offeringId,
      faculty_user_id: facultyId,
      starts_on: startsOn,
      planned_end_on: plannedEnd || null,
    })
    if (!failure) setOfferingId('')
  }

  return (
    <form
      onSubmit={(event) => void submit(event)}
      aria-labelledby={`${id}-title`}
      className="space-y-3 rounded-xl border border-line bg-surface p-4"
    >
      <h3 id={`${id}-title`} className="text-sm font-semibold text-content">
        Assign teaching
      </h3>
      <div className="grid gap-3 md:grid-cols-2">
        <label className={LABEL}>
          Faculty member
          <select value={facultyId} onChange={(event) => setFacultyId(event.target.value)} className={SELECT_CLASS}>
            <option value="">Choose faculty…</option>
            {model.faculty.map((item) => (
              <option key={item.user_id} value={item.user_id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label className={LABEL}>
          Subject and class
          <select
            value={offeringId}
            disabled={model.offerings.length === 0}
            onChange={(event) => setOfferingId(event.target.value)}
            className={SELECT_CLASS}
          >
            <option value="">Choose subject…</option>
            {[...new Set(model.offerings.map((item) => item.department_name))].map((department) => (
              <optgroup key={department} label={department}>
                {model.offerings
                  .filter((item) => item.department_name === department)
                  .map((item) => (
                    <option key={item.academic_offering_id} value={item.academic_offering_id}>
                      {offeringLabel(item)}
                    </option>
                  ))}
              </optgroup>
            ))}
          </select>
        </label>
        <label className={LABEL}>
          Starts on
          <input
            type="date"
            required
            value={startsOn}
            onChange={(event) => setStartsOn(event.target.value)}
            className={SELECT_CLASS}
          />
        </label>
        <label className={LABEL}>
          Planned end (optional)
          <input
            type="date"
            value={plannedEnd}
            min={startsOn > todayIso() ? startsOn : todayIso()}
            aria-invalid={datesWrong || undefined}
            onChange={(event) => setPlannedEnd(event.target.value)}
            className={SELECT_CLASS}
          />
        </label>
      </div>
      {model.offerings.length === 0 && !model.optionsError ? (
        <p className="text-xs text-warning">No active subject offerings yet. Add them in Academic Setup.</p>
      ) : null}
      {datesWrong ? (
        <p className="text-xs text-danger">The planned end must be on or after today and the start date.</p>
      ) : null}
      {outcome === 'pending' && offering ? (
        <p role="status" className="text-xs text-info">
          {offering.department_name} is not one of this teacher’s departments, so the request waits for the{' '}
          {offering.department_name} Head of Department to approve it.
        </p>
      ) : null}
      {outcome === 'refused' ? (
        <p role="status" className="text-xs text-danger">
          You can assign teaching only in departments you head, or for teachers of your departments.
        </p>
      ) : null}
      <div className="flex justify-end">
        <button type="submit" disabled={sending || blocked} className={PRIMARY_BUTTON_CLASS}>
          {sending ? 'Sending…' : outcome === 'pending' ? 'Send for approval' : 'Assign'}
        </button>
      </div>
    </form>
  )
}
