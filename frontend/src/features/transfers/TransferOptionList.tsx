import type { TransferOption, TransferType } from '../../types/transfer.ts'
import { TRANSFER_TYPE_LABEL, describeSection, seatSummary } from './transferLabels.ts'

const GROUPS: { type: TransferType; hint: string }[] = [
  { type: 'section_transfer', hint: 'Another section of the same batch and program.' },
  { type: 'program_transfer', hint: 'A section of a different program in the same term.' },
]

/** Target sections grouped by transfer type; full sections cannot be chosen. */
export default function TransferOptionList({
  name,
  options,
  value,
  disabled,
  onChange,
}: {
  name: string
  options: TransferOption[]
  value: string
  disabled: boolean
  onChange: (sectionId: string) => void
}) {
  return (
    <>
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
                  name={name}
                  className="mt-1"
                  value={option.academic_section_id}
                  checked={value === option.academic_section_id}
                  disabled={!option.has_seat || disabled}
                  onChange={() => onChange(option.academic_section_id)}
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
    </>
  )
}
