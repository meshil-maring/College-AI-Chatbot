import { useId, useState } from 'react'
import type { TransferOption, TransferSubmit, TransferType } from '../../../types/transfer.ts'
import { TRANSFER_TYPE_LABEL, describeSection, seatSummary } from '../../transfers/transferLabels.ts'

const GROUPS: { type: TransferType; hint: string }[] = [
  { type: 'section_transfer', hint: 'Another section of your current batch and program.' },
  { type: 'program_transfer', hint: 'A section of a different program in the same term.' },
]

export default function TransferForm({
  options,
  registered,
  busy,
  onSubmit,
  onCancel,
}: {
  options: TransferOption[]
  registered: boolean
  busy: boolean
  onSubmit: (body: TransferSubmit) => void
  onCancel: () => void
}) {
  const id = useId()
  const [target, setTarget] = useState('')
  const [reason, setReason] = useState('')
  const [acknowledged, setAcknowledged] = useState(false)
  const trimmed = reason.trim()
  const chosen = options.find((option) => option.academic_section_id === target)
  const canSubmit = Boolean(chosen?.has_seat) && trimmed.length >= 10 && acknowledged && !busy
  return (
    <form
      className="ui-panel space-y-5 p-4 sm:p-5"
      aria-label="Request a transfer"
      onSubmit={(event) => {
        event.preventDefault()
        if (canSubmit) onSubmit({ to_section_id: target, reason: trimmed })
      }}
    >
      {GROUPS.map(({ type, hint }) => {
        const group = options.filter((option) => option.transfer_type === type)
        if (!group.length) return null
        return (
          <fieldset key={type} className="space-y-2">
            <legend className="font-semibold text-content">{TRANSFER_TYPE_LABEL[type]}</legend>
            <p className="text-sm text-muted">{hint}</p>
            {group.map((option) => (
              <label
                key={option.academic_section_id}
                className={`flex min-h-11 items-start gap-3 rounded-lg border border-line p-3 ${
                  option.has_seat ? 'cursor-pointer hover:bg-hover' : 'opacity-60'
                }`}
              >
                <input
                  type="radio"
                  name={`${id}-target`}
                  className="mt-1"
                  value={option.academic_section_id}
                  checked={target === option.academic_section_id}
                  disabled={!option.has_seat || busy}
                  onChange={() => setTarget(option.academic_section_id)}
                />
                <span className="min-w-0">
                  <span className="block text-content">{describeSection(option)}</span>
                  <span className="block text-xs text-muted">
                    {option.department_name} · {option.has_seat ? seatSummary(option) : 'Full'}
                  </span>
                </span>
              </label>
            ))}
          </fieldset>
        )
      })}

      <div>
        <label htmlFor={`${id}-reason`} className="mb-1 block font-semibold text-content">
          Reason for the transfer
        </label>
        <textarea
          id={`${id}-reason`}
          rows={4}
          maxLength={2000}
          value={reason}
          disabled={busy}
          onChange={(event) => setReason(event.target.value)}
          aria-describedby={`${id}-reason-hint`}
          className="w-full rounded-lg border border-control bg-surface px-3 py-2 text-content"
        />
        <p id={`${id}-reason-hint`} className="text-xs text-muted">
          At least 10 characters. The reviewing HOD or administrator will read this.
        </p>
      </div>

      <label className="flex items-start gap-2 text-sm text-content">
        <input
          type="checkbox"
          className="mt-1"
          checked={acknowledged}
          disabled={busy}
          onChange={(event) => setAcknowledged(event.target.checked)}
        />
        <span>
          I understand that if this transfer is approved my section changes immediately
          {registered ? ' and I must register my subjects again in the new section' : ''}.
        </span>
      </label>

      <div className="flex flex-wrap justify-end gap-2">
        <button
          type="button"
          className="min-h-11 rounded-lg border border-control px-4 py-2 hover:bg-hover"
          disabled={busy}
          onClick={onCancel}
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={!canSubmit}
          className="min-h-11 rounded-lg bg-accent px-4 py-2 font-medium text-ink hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? 'Submitting…' : 'Submit request'}
        </button>
      </div>
    </form>
  )
}
