import { Mail } from 'lucide-react'
import { PlacementStep } from '../placement/PlacementStep.tsx'
import { shortPlacementLabel } from '../placement/PlacementSummary.tsx'
import type { PlacementOptions } from '../placement/usePlacementOptions.ts'
import StudentOnboardingWorkflowHeader from '../shared/StudentOnboardingWorkflowHeader.tsx'
import CompletionCard from './CompletionCard.tsx'
import DuplicatePrecheckNotice from './DuplicatePrecheckNotice.tsx'
import DuplicateStudentConflictNotice from './DuplicateStudentConflictNotice.tsx'
import StudentIdentityForm from './StudentIdentityForm.tsx'
import StudentInvitationReview from './StudentInvitationReview.tsx'
import { RESULT_STEP, REVIEW_STEP, type SingleRegistration } from './useSingleRegistration.ts'

export default function SingleRegistrationWorkflow({
  registration,
  placement,
  resending,
  onResend,
}: {
  registration: SingleRegistration
  placement: PlacementOptions
  resending: boolean
  onResend: (invitationId: string) => Promise<'sent' | 'failed' | null>
}) {
  const { step, goTo, student, sectionId, error, busy } = registration
  const { selectedSection, selectedCohort } = placement
  const placementLabel = shortPlacementLabel(selectedCohort, selectedSection)
  const duplicateError = error.includes('already in use')

  return (
    <section className="student-onboarding-workflow" aria-label="Single student registration">
      <StudentOnboardingWorkflowHeader
        mode="single"
        activeStep={step}
        onSelectStep={busy || step === RESULT_STEP ? undefined : goTo}
      />
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
          placementLabel={placementLabel}
          onFieldChange={registration.setField}
          onBack={() => goTo(0)}
          onContinue={() => goTo(REVIEW_STEP)}
        />
      )}
      {step === REVIEW_STEP && selectedSection && (
        <div className="student-onboarding-stage">
          <StudentInvitationReview student={student} section={selectedSection} batchCode={selectedCohort?.code ?? ''} />
          {duplicateError ? (
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
          ) : (
            <DuplicatePrecheckNotice
              review={registration.identityReview}
              reviewing={registration.identityReviewing}
              onEdit={() => goTo(1)}
            />
          )}
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
      {step === RESULT_STEP && (
        <CompletionCard
          sent={registration.delivery === 'sent'}
          email={student.email}
          placementLabel={placementLabel}
          resending={resending}
          onAgain={registration.registerAnother}
          onChangePlacement={() => {
            registration.registerAnother()
            goTo(0)
          }}
          onResend={
            registration.invitationId
              ? () =>
                  void onResend(registration.invitationId).then((status) => {
                    if (status === 'sent') registration.markDelivered()
                  })
              : undefined
          }
        />
      )}
    </section>
  )
}
