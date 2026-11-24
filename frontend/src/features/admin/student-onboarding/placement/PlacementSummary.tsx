/** Reminder of the chosen batch and section, with a way back to the placement step. */
export default function PlacementSummary({
  label,
  disabled,
  onChange,
}: {
  label: string
  disabled: boolean
  onChange: () => void
}) {
  if (!label) return null
  return (
    <div className="student-onboarding-placement-summary">
      <span>
        Placing in <strong>{label}</strong>
      </span>
      <button type="button" className="student-onboarding-text-button" disabled={disabled} onClick={onChange}>
        Change
      </button>
    </div>
  )
}

/** Short "BATCH / SECTION · Section name" label used in summaries and results. */
export function shortPlacementLabel(cohort?: { code: string }, section?: { code: string; name: string }): string {
  return cohort && section ? `${cohort.code} / ${section.code} · ${section.name}` : ''
}
