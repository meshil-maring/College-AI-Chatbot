import { Check, Mail, UsersRound } from 'lucide-react'
import type { AcademicSection, AdmissionCohort } from '../../../types/academicStructure.ts'
import type { StudentImportRow } from './studentImport.ts'

export function PlacementStep({
  sections,
  cohorts,
  selectedSection,
  selectedLabel,
  loading,
  sectionId,
  onChange,
  onContinue,
  continueLabel,
}: {
  sections: AcademicSection[]
  cohorts: AdmissionCohort[]
  selectedSection?: AcademicSection
  selectedLabel: string
  loading: boolean
  sectionId: string
  onChange: (id: string) => void
  onContinue: () => void
  continueLabel: string
}) {
  return (
    <div className="student-onboarding-stage">
      <div className="student-onboarding-form-heading">
        <span className="student-onboarding-eyebrow">STEP 1 · ACADEMIC PLACEMENT</span>
        <h3>Where should this student be enrolled?</h3>
        <p>Choose an active batch and section. This assignment is applied to every student in this registration.</p>
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
            <small>Students will be added to</small>
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

export function CompletionCard({ sent, email, onAgain }: { sent: boolean; email: string; onAgain: () => void }) {
  return (
    <div
      className={`student-onboarding-completion ${sent ? 'is-success' : 'is-warning'}`}
      role="region"
      aria-label="Registration result"
    >
      <span className="student-onboarding-completion-icon">{sent ? <Check size={24} /> : <Mail size={24} />}</span>
      <span className="student-onboarding-eyebrow">{sent ? 'INVITATION SENT' : 'DELIVERY NEEDS ATTENTION'}</span>
      <h3>{sent ? 'Student registration is underway' : 'The account was created, but the email did not send'}</h3>
      <p>
        {sent
          ? `A secure setup link was sent to ${email}.`
          : `You can resend a fresh setup link from Pending invitations for ${email}.`}
      </p>
      <button type="button" className="student-onboarding-secondary" onClick={onAgain}>
        Register another student
      </button>
    </div>
  )
}

export function BulkResults({
  results,
  remaining,
  onFix,
  onStartOver,
}: {
  results: { row: number; status: string; delivery_status: 'sent' | 'failed' | null; message: string }[]
  remaining: StudentImportRow[]
  onFix: () => void
  onStartOver: () => void
}) {
  const created = results.filter((item) => item.status === 'created').length
  const sent = results.filter((item) => item.delivery_status === 'sent').length
  return (
    <div className="student-onboarding-results" role="region" aria-live="polite" aria-label="Bulk registration results">
      <span
        className={`student-onboarding-completion-icon ${remaining.length || results.some((item) => item.delivery_status === 'failed') ? 'is-warning' : 'is-success'}`}
      >
        {remaining.length || results.some((item) => item.delivery_status === 'failed') ? (
          <UsersRound size={24} />
        ) : (
          <Check size={24} />
        )}
      </span>
      <span className="student-onboarding-eyebrow">BULK REGISTRATION RESULTS</span>
      <h3>
        {remaining.length
          ? 'Some students still need attention'
          : results.some((item) => item.delivery_status === 'failed')
            ? 'Some setup emails need to be resent'
            : 'Student invitations processed'}
      </h3>
      <div className="student-onboarding-result-counts">
        <span>
          <strong>{created}</strong>
          <small>Invitations created</small>
        </span>
        <span>
          <strong>{sent}</strong>
          <small>Setup emails sent</small>
        </span>
        <span>
          <strong>{remaining.length}</strong>
          <small>Rows to review</small>
        </span>
      </div>
      {results.length > 0 && (
        <ul className="student-onboarding-result-list">
          {results.map((item) => (
            <li
              key={item.row}
              className={item.status === 'created' && item.delivery_status === 'sent' ? 'is-created' : 'has-issues'}
            >
              <strong>Row {item.row}</strong>
              <span>
                {item.status === 'created'
                  ? item.delivery_status === 'sent'
                    ? 'Invitation sent'
                    : 'Email needs retry'
                  : item.status}
              </span>
              <small>{item.message}</small>
            </li>
          ))}
        </ul>
      )}
      {remaining.length > 0 && (
        <div className="student-onboarding-unresolved">
          <strong>Rows still in review</strong>
          {remaining.map((row) => (
            <p key={row.sourceRow}>
              Row {row.sourceRow}: {row.errors.join(' ') || 'Invitation could not be created.'}
            </p>
          ))}
        </div>
      )}
      <div className="student-onboarding-stage-actions">
        {remaining.length > 0 && (
          <button type="button" className="student-onboarding-secondary" onClick={onFix}>
            Fix remaining rows
          </button>
        )}
        <button type="button" className="student-onboarding-primary" onClick={onStartOver}>
          Start another upload
        </button>
      </div>
    </div>
  )
}
