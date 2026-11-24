import { Check } from 'lucide-react'
import type { PlacementOptions } from './usePlacementOptions.ts'

export function PlacementStep({
  placement,
  sectionId,
  plural,
  onChange,
  onContinue,
  continueLabel,
}: {
  placement: PlacementOptions
  sectionId: string
  /** Bulk import places every uploaded student in the same section. */
  plural: boolean
  onChange: (id: string) => void
  onContinue: () => void
  continueLabel: string
}) {
  const { sections, cohorts, selectedSection, selectedLabel, loading } = placement
  return (
    <div className="student-onboarding-stage">
      <div className="student-onboarding-form-heading">
        <h2>{plural ? 'Where should these students be enrolled?' : 'Where should this student be enrolled?'}</h2>
        <p>
          {plural
            ? 'Choose an active batch and section. Every student in the file is placed here.'
            : 'Choose an active batch and section for the new student.'}
        </p>
      </div>
      <label className="student-onboarding-section-select">
        <span>
          Batch and section <b aria-hidden="true">*</b>
        </span>
        <select required value={sectionId} disabled={loading} onChange={(event) => onChange(event.target.value)}>
          <option value="">{loading ? 'Loading active sections…' : 'Select a batch and section'}</option>
          {sections.map((section) => {
            const cohort = cohorts.find((item) => item.admission_cohort_id === section.admission_cohort_id)
            return (
              <option key={section.academic_section_id} value={section.academic_section_id}>
                {cohort?.code ?? 'Batch'} · {cohort?.name ?? 'Unknown batch'} · {section.code} {section.name}
              </option>
            )
          })}
        </select>
        <small>Only active sections are available. The selected batch code appears in the student email.</small>
      </label>
      {selectedSection && (
        <div className="student-onboarding-placement-card">
          <span className="student-onboarding-placement-mark">{selectedLabel.split(' · ')[0]}</span>
          <div>
            <small>{plural ? 'Students will be added to' : 'The student will be added to'}</small>
            <strong>{selectedLabel}</strong>
          </div>
          <Check size={18} aria-hidden="true" />
        </div>
      )}
      {!loading && !sections.length && (
        <p className="student-onboarding-empty-note" role="status">
          Create an active batch and section in Academic Setup before registering students.
        </p>
      )}
      <StageActions canContinue={!!sectionId} onContinue={onContinue} continueLabel={continueLabel} />
    </div>
  )
}

export function StageActions({
  onBack,
  onContinue,
  canContinue,
  continueLabel,
}: {
  onBack?: () => void
  onContinue: () => void
  canContinue: boolean
  continueLabel: string
}) {
  return (
    <div className="student-onboarding-stage-actions">
      <span className="student-onboarding-step-hint">You can review everything before sending.</span>
      <div>
        {onBack && (
          <button type="button" className="student-onboarding-secondary" onClick={onBack}>
            Back
          </button>
        )}
        <button type="button" className="student-onboarding-primary" disabled={!canContinue} onClick={onContinue}>
          {continueLabel} <span aria-hidden="true">→</span>
        </button>
      </div>
    </div>
  )
}
