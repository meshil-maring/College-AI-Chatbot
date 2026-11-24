import { Mail } from 'lucide-react'
import { PlacementStep } from '../placement/PlacementStep.tsx'
import type { PlacementOptions } from '../placement/usePlacementOptions.ts'
import StudentOnboardingWorkflowHeader from '../shared/StudentOnboardingWorkflowHeader.tsx'
import CompletionCard from './CompletionCard.tsx'
import DuplicateStudentConflictNotice from './DuplicateStudentConflictNotice.tsx'
import StudentIdentityForm from './StudentIdentityForm.tsx'
import StudentInvitationReview from './StudentInvitationReview.tsx'
import type { SingleRegistration } from './useSingleRegistration.ts'

export default function SingleRegistrationWorkflow({
  registration,
  placement,
}: {
  registration: SingleRegistration
  placement: PlacementOptions
}) {
  const { step, goTo, student, sectionId, error, busy } = registration
  const { selectedSection, selectedCohort } = placement

  return (
    <section className="student-onboarding-workflow" aria-label="Single student registration">
      <StudentOnboardingWorkflowHeader mode="single" activeStep={step} />
      {placement.error && (
        <p className="student-onboarding-inline-error" role="alert">
          {placement.error}
        </p>
      )}
      {step === 0 && (
        <PlacementStep
          placement={placement}
          sectionId={sectionId}
          plural={false}
          onChange={registration.setSectionId}
          continueLabel="Continue to student details"
          onContinue={() => goTo(1)}
        />
      )}
      {step === 1 && (
        <StudentIdentityForm
          student={student}
          busy={busy}
          hasSection={!!sectionId}
          onFieldChange={registration.setField}
          onBack={() => goTo(0)}
          onContinue={() => goTo(2)}
        />
      )}
      {step === 2 && selectedSection && (
        <div className="student-onboarding-stage">
          <StudentInvitationReview student={student} section={selectedSection} batchCode={selectedCohort?.code ?? ''} />
          {error && error.includes('already in use') ? (
            <DuplicateStudentConflictNotice
              message={error}
              review={registration.identityReview}
              reviewError={registration.identityReviewError}
              reviewing={registration.identityReviewing}
            />
          ) : error ? (
            <p className="student-onboarding-inline-error" role="alert">
              {error}
            </p>
          ) : null}
          <div className="student-onboarding-stage-actions">
            <button type="button" className="student-onboarding-secondary" disabled={busy} onClick={() => goTo(1)}>
              Back to details
            </button>
            <button
              type="button"
              className="student-onboarding-primary"
              disabled={busy}
              onClick={() => void registration.submit()}
            >
              <Mail size={17} /> {busy ? 'Sending setup link…' : 'Create account & send link'}
            </button>
          </div>
        </div>
      )}
      {step === 3 && (
        <CompletionCard sent={registration.delivery === 'sent'} email={student.email} onAgain={registration.reset} />
      )}
    </section>
  )
}
