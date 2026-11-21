import { useId, useState } from 'react'
import type { DirectTransferOptions } from '../../../types/transfer.ts'
import TransferOptionList from '../TransferOptionList.tsx'
import { describeSection } from '../transferLabels.ts'

/**
 * Choose the target section and reason; submitting moves the student immediately.
 * Same-semester sections are the default. An administrator may reveal other
 * semesters, which needs a separate override confirmation.
 */
export default function DirectTransferForm({
  studentName,
  data,
  busy,
  onSubmit,
}: {
  studentName: string
  data: DirectTransferOptions
  busy: boolean
  onSubmit: (toSectionId: string, reason: string, allowOtherSemester: boolean) => void
}) {
  const id = useId()
  const [target, setTarget] = useState('')
  const [reason, setReason] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [showOther, setShowOther] = useState(false)
  const [overrideConfirmed, setOverrideConfirmed] = useState(false)
  const same = data.options.filter((option) => option.same_semester !== false)
  const other = data.can_override_semester ? data.options.filter((option) => option.same_semester === false) : []
  const chosen = data.options.find((option) => option.academic_section_id === target)
  const crossSemester = chosen?.same_semester === false
  const trimmed = reason.trim()
  const canSubmit =
    Boolean(chosen?.has_seat) && trimmed.length >= 10 && confirmed && (!crossSemester || overrideConfirmed) && !busy
  const semester = data.current.program_semester_name
  return (
    <form
      className="space-y-5"
      aria-label={`Transfer ${studentName}`}
      onSubmit={(event) => {
        event.preventDefault()
        if (canSubmit) onSubmit(target, trimmed, crossSemester)
      }}
    >
      {same.length ? (
        <TransferOptionList name={`${id}-target`} options={same} value={target} disabled={busy} onChange={setTarget} />
      ) : (
        <p role="status">
          {data.actor_role === 'hod'
            ? `No other open ${semester} section in your department is available for this student.`
            : `No other open ${semester} section is available for this student in the current term.`}
        </p>
      )}
      {other.length > 0 && (
        <div className="space-y-3 rounded-lg border border-line p-3">
          <label className="flex items-start gap-2 text-sm text-content">
            <input
              type="checkbox"
              className="mt-1"
              checked={showOther}
              disabled={busy}
              onChange={(event) => {
                setShowOther(event.target.checked)
                if (!event.target.checked && crossSemester) setTarget('')
              }}
            />
            <span>Show other semesters (administrator override)</span>
          </label>
          {showOther && (
            <>
              <p className="text-sm text-warning">
                Transfers normally keep the student in {semester}. Use these only for approved cases such as lateral
                entry.
              </p>
              <TransferOptionList
                name={`${id}-target`}
                options={other}
                value={target}
                disabled={busy}
                onChange={setTarget}
              />
            </>
          )}
        </div>
      )}
      <div>
        <label htmlFor={`${id}-reason`} className="mb-1 block font-semibold text-content">
          Reason (shown to the student)
        </label>
        <textarea
          id={`${id}-reason`}
          rows={3}
          maxLength={2000}
          value={reason}
          disabled={busy}
          onChange={(event) => setReason(event.target.value)}
          className="w-full rounded-lg border border-control bg-surface px-3 py-2 text-content"
        />
        <p className="text-xs text-muted">At least 10 characters.</p>
      </div>
      {crossSemester && chosen && (
        <label className="flex items-start gap-2 text-sm text-warning">
          <input
            type="checkbox"
            className="mt-1"
            checked={overrideConfirmed}
            disabled={busy}
            onChange={(event) => setOverrideConfirmed(event.target.checked)}
          />
          <span>
            I confirm moving {studentName} from {semester} to {chosen.program_semester_name}. This override is recorded.
          </span>
        </label>
      )}
      <label className="flex items-start gap-2 text-sm text-content">
        <input
          type="checkbox"
          className="mt-1"
          checked={confirmed}
          disabled={busy}
          onChange={(event) => setConfirmed(event.target.checked)}
        />
        <span>
          Move {studentName} out of {describeSection(data.current)} now. No approval is needed
          {data.current.registration_status === 'registered'
            ? ', and their registered subjects for this term are cleared so they register again'
            : ''}
          .
        </span>
      </label>
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={!canSubmit}
          className="min-h-11 rounded-lg bg-accent px-4 py-2 font-medium text-ink hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? 'Transferring…' : 'Transfer student'}
        </button>
      </div>
    </form>
  )
}
