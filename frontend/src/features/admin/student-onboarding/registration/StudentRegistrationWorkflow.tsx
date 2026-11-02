import { Check, Mail } from 'lucide-react'
import StudentIdentityForm from '../StudentIdentityForm.tsx'
import StudentImportReview from '../StudentImportReview.tsx'
import StudentImportUpload from '../StudentImportUpload.tsx'
import StudentInvitationReview from '../StudentInvitationReview.tsx'
import StudentOnboardingWorkflowHeader, { registrationSteps } from '../StudentOnboardingWorkflowHeader.tsx'
import { StudentRegistrationModePicker } from '../StudentOnboardingProgress.tsx'
import { BulkResults, CompletionCard, PlacementStep } from '../StudentOnboardingStages.tsx'
import type { useStudentOnboarding } from '../useStudentOnboarding.ts'
import DuplicateStudentConflictNotice from './DuplicateStudentConflictNotice.tsx'

type Model = ReturnType<typeof useStudentOnboarding>

export default function StudentRegistrationWorkflow({ model, bulkOnly }: { model: Model; bulkOnly: boolean }) {
  const {
    structure,
    mode,
    sectionId,
    setSectionId,
    singleStep,
    setSingleStep,
    bulkStep,
    setBulkStep,
    student,
    singleDelivery,
    rows,
    fileName,
    fileError,
    bulkResults,
    notice,
    error,
    identityReview,
    identityReviewError,
    identityReviewing,
    busy,
    cohorts,
    sections,
    selectedSection,
    selectedCohort,
    selectedLabel,
    readyRows,
    issueRows,
    changeMode,
    setField,
    upload,
    editRow,
    removeRow,
    submitSingle,
    submitBulk,
    resetSingle,
    resetBulk,
  } = model

  return (
    <div className="student-onboarding-form-panel">
      {!bulkOnly && <StudentRegistrationModePicker mode={mode} disabled={busy} onChange={changeMode} />}
      <section
        className="student-onboarding-workflow"
        aria-label={mode === 'single' ? 'Single student registration' : 'Bulk student registration'}
      >
        <StudentOnboardingWorkflowHeader
          mode={mode}
          fileName={fileName}
          steps={registrationSteps[mode]}
          activeStep={mode === 'single' ? singleStep : bulkStep}
        />
        {structure.error instanceof Error && (
          <p className="student-onboarding-inline-error" role="alert">
            {structure.error.message}
          </p>
        )}
        {(mode === 'single' ? singleStep === 0 : bulkStep === 0) && (
          <PlacementStep
            sections={sections}
            cohorts={cohorts}
            selectedSection={selectedSection}
            selectedLabel={selectedLabel}
            loading={structure.isPending}
            sectionId={sectionId}
            onChange={setSectionId}
            continueLabel={mode === 'single' ? 'Continue to student details' : 'Continue to upload'}
            onContinue={() => (mode === 'single' ? setSingleStep(1) : setBulkStep(1))}
          />
        )}
        {mode === 'single' && singleStep === 1 && (
          <StudentIdentityForm
            student={student}
            busy={busy}
            hasSection={!!sectionId}
            onFieldChange={setField}
            onContinue={() => setSingleStep(2)}
          />
        )}
        {mode === 'single' && singleStep === 2 && selectedSection && (
          <div className="student-onboarding-stage">
            <StudentInvitationReview
              student={student}
              section={selectedSection}
              batchCode={selectedCohort?.code ?? ''}
            />
            {error && error.includes('already in use') ? (
              <DuplicateStudentConflictNotice
                message={error}
                review={identityReview}
                reviewError={identityReviewError}
                reviewing={identityReviewing}
              />
            ) : error ? (
              <p className="student-onboarding-inline-error" role="alert">
                {error}
              </p>
            ) : null}
            <div className="student-onboarding-stage-actions">
              <button
                type="button"
                className="student-onboarding-secondary"
                disabled={busy}
                onClick={() => setSingleStep(1)}
              >
                Back to details
              </button>
              <button
                type="button"
                className="student-onboarding-primary"
                disabled={busy}
                onClick={() => void submitSingle()}
              >
                <Mail size={17} /> {busy ? 'Sending setup link…' : 'Create account & send link'}
              </button>
            </div>
          </div>
        )}
        {mode === 'single' && singleStep === 3 && (
          <CompletionCard sent={singleDelivery === 'sent'} email={student.email} onAgain={resetSingle} />
        )}
        {mode === 'bulk' && bulkStep === 1 && (
          <div className="student-onboarding-stage">
            <StudentImportUpload
              fileName={fileName}
              error={fileError}
              disabled={busy}
              onFile={(file) => void upload(file)}
            />
            <div className="student-onboarding-stage-actions">
              <button type="button" className="student-onboarding-secondary" onClick={() => setBulkStep(0)}>
                Back to placement
              </button>
              <button
                type="button"
                className="student-onboarding-primary"
                disabled={!rows.length}
                onClick={() => setBulkStep(2)}
              >
                Review student list <span aria-hidden="true">→</span>
              </button>
            </div>
          </div>
        )}
        {mode === 'bulk' && bulkStep === 2 && (
          <div className="student-onboarding-stage">
            <div className="student-onboarding-review-summary" aria-live="polite">
              <span>
                <strong>{rows.length}</strong> total students
              </span>
              <span className="is-ready">
                <Check size={16} /> {readyRows.length} ready
              </span>
              {issueRows > 0 && <span className="has-issues">{issueRows} need attention</span>}
            </div>
            <p className="student-onboarding-helper">
              Review the imported details below. Fix highlighted rows or remove them; only ready students will be
              invited.
            </p>
            <StudentImportReview rows={rows} disabled={busy} onEdit={editRow} onRemove={removeRow} />
            {error && (
              <p className="student-onboarding-inline-error" role="alert">
                {error}
              </p>
            )}
            <div className="student-onboarding-stage-actions">
              <button
                type="button"
                className="student-onboarding-secondary"
                disabled={busy}
                onClick={() => setBulkStep(1)}
              >
                Back to upload
              </button>
              <button
                type="button"
                className="student-onboarding-primary"
                disabled={busy || !readyRows.length}
                onClick={() => void submitBulk()}
              >
                <Mail size={17} />{' '}
                {busy
                  ? 'Sending setup links…'
                  : `Invite ${readyRows.length} ready student${readyRows.length === 1 ? '' : 's'}`}
              </button>
            </div>
          </div>
        )}
        {mode === 'bulk' && bulkStep === 3 && (
          <BulkResults results={bulkResults} remaining={rows} onFix={() => setBulkStep(2)} onStartOver={resetBulk} />
        )}
      </section>
      {notice && (
        <p className="student-onboarding-notice" role="status">
          {notice}
        </p>
      )}
      {error && mode === 'single' && singleStep !== 2 && (
        <p className="student-onboarding-inline-error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
