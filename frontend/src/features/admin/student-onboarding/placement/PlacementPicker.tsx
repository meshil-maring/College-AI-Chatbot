import { useState } from 'react'
import type { PlacementOptions } from './usePlacementOptions.ts'

/**
 * Two-level placement: pick a batch, then one of its active sections.
 * A batch with a single section selects it automatically.
 */
export default function PlacementPicker({
  placement,
  sectionId,
  onChange,
}: {
  placement: PlacementOptions
  sectionId: string
  onChange: (id: string) => void
}) {
  const { cohorts, sections, selectedCohort, loading } = placement
  const [batchId, setBatchId] = useState(selectedCohort?.admission_cohort_id ?? '')
  const batches = cohorts.filter((cohort) =>
    sections.some((section) => section.admission_cohort_id === cohort.admission_cohort_id),
  )
  const batchSections = sections.filter((section) => section.admission_cohort_id === batchId)

  function chooseBatch(nextBatchId: string) {
    setBatchId(nextBatchId)
    const nextSections = sections.filter((section) => section.admission_cohort_id === nextBatchId)
    onChange(nextSections.length === 1 ? nextSections[0].academic_section_id : '')
  }

  return (
    <div className="student-onboarding-placement-picker">
      <label className="student-onboarding-section-select">
        <span>
          Batch <b aria-hidden="true">*</b>
        </span>
        <select
          required
          value={batchId}
          disabled={loading || !batches.length}
          onChange={(event) => chooseBatch(event.target.value)}
        >
          <option value="">{loading ? 'Loading active batches…' : 'Select a batch'}</option>
          {batches.map((cohort) => (
            <option key={cohort.admission_cohort_id} value={cohort.admission_cohort_id}>
              {cohort.code} · {cohort.name}
            </option>
          ))}
        </select>
        <small>Only active batches with an active section are listed. The batch code appears in the email.</small>
      </label>
      {batchId && (
        <fieldset className="student-onboarding-section-choices">
          <legend>
            Section <b aria-hidden="true">*</b>
          </legend>
          {batchSections.length ? (
            <div role="presentation">
              {batchSections.map((section) => (
                <label key={section.academic_section_id}>
                  <input
                    type="radio"
                    name="student-onboarding-section"
                    value={section.academic_section_id}
                    checked={sectionId === section.academic_section_id}
                    onChange={() => onChange(section.academic_section_id)}
                  />
                  <span>
                    <strong>{section.code}</strong>
                    <small>{section.name}</small>
                  </span>
                </label>
              ))}
            </div>
          ) : (
            <p className="student-onboarding-empty-note">This batch has no active sections.</p>
          )}
        </fieldset>
      )}
    </div>
  )
}
