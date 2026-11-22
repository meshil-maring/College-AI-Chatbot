import { useId, useState, type FormEvent } from 'react'
import type { MembershipRosterEntry } from '../../../../types/admin.ts'
import type { ResponsibilityKind } from '../../../../types/admin/responsibilities.ts'
import HodTermFields, { termError, todayIso } from '../roster/HodTermFields.tsx'
import { PRIMARY_BUTTON_CLASS, SELECT_CLASS } from '../StaffFacultyUI.tsx'
import type { MemberResponsibilitiesModel } from './useMemberResponsibilities.ts'

export const RESPONSIBILITY_LABELS: Record<ResponsibilityKind, string> = {
  class_in_charge: 'Class In-Charge',
  subject_coordinator: 'Subject Coordinator',
}

interface Props {
  model: MemberResponsibilitiesModel
  /** Active Faculty members who can be appointed. */
  faculty: MembershipRosterEntry[]
}

/** Appoint a Faculty member as Class In-Charge of a section or Subject Coordinator of a course. */
export default function AssignResponsibilityForm({ model, faculty }: Props) {
  const id = useId()
  const [kind, setKind] = useState<ResponsibilityKind>('class_in_charge')
  const [facultyId, setFacultyId] = useState('')
  const [targetId, setTargetId] = useState('')
  const [term, setTerm] = useState({ starts_on: todayIso(), planned_end_on: null as string | null })
  const targets = kind === 'class_in_charge' ? model.sections : model.courses
  const sending = model.actionKey === 'assign'
  const blocked = !facultyId || !targetId || termError(term) !== null

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (blocked) return
    const failure = await model.assign({
      faculty_user_id: facultyId,
      responsibility: kind,
      target_id: targetId,
      ...term,
    })
    if (!failure) setTargetId('')
  }

  const labelClass = 'flex flex-col gap-1 text-sm font-medium text-content'
  return (
    <form
      onSubmit={(event) => void submit(event)}
      aria-labelledby={`${id}-title`}
      className="space-y-3 rounded-xl border border-line bg-surface p-4"
    >
      <h3 id={`${id}-title`} className="text-sm font-semibold text-content">
        Assign a responsibility
      </h3>
      <div className="grid gap-3 md:grid-cols-3">
        <label className={labelClass}>
          Responsibility
          <select
            value={kind}
            onChange={(event) => {
              setKind(event.target.value as ResponsibilityKind)
              setTargetId('')
            }}
            className={SELECT_CLASS}
          >
            {Object.entries(RESPONSIBILITY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className={labelClass}>
          Faculty member
          <select value={facultyId} onChange={(event) => setFacultyId(event.target.value)} className={SELECT_CLASS}>
            <option value="">Choose faculty…</option>
            {faculty.map((member) => (
              <option key={member.user_id} value={member.user_id}>
                {member.name || member.email}
              </option>
            ))}
          </select>
        </label>
        <label className={labelClass}>
          {kind === 'class_in_charge' ? 'Class section' : 'Course'}
          <select
            value={targetId}
            disabled={targets.length === 0}
            onChange={(event) => setTargetId(event.target.value)}
            className={SELECT_CLASS}
          >
            <option value="">{kind === 'class_in_charge' ? 'Choose section…' : 'Choose course…'}</option>
            {targets.map((target) => (
              <option key={target.id} value={target.id}>
                {target.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {targets.length === 0 ? (
        <p className="text-xs text-warning">
          {kind === 'class_in_charge'
            ? 'No active class sections yet. Add them in Academic Setup.'
            : 'No active courses yet. Add them in Academic Setup.'}
        </p>
      ) : null}
      {faculty.length === 0 ? <p className="text-xs text-warning">There are no active Faculty members yet.</p> : null}
      <HodTermFields
        id={`${id}-term`}
        label="this appointment"
        term={term}
        disabled={sending}
        indent={false}
        onChange={setTerm}
      />
      <p className="text-xs text-muted">
        A section or course has one current holder; assigning someone else hands it over and keeps the history.
      </p>
      <div className="flex justify-end">
        <button type="submit" disabled={sending || blocked} className={PRIMARY_BUTTON_CLASS}>
          {sending ? 'Assigning…' : 'Assign'}
        </button>
      </div>
    </form>
  )
}
