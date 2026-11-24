import { FileSpreadsheet } from 'lucide-react'
import InvitationMetrics from '../invitations/InvitationMetrics.tsx'
import StudentInvitationList from '../invitations/StudentInvitationList.tsx'
import { useStudentInvitations } from '../invitations/useStudentInvitations.ts'
import { usePlacementOptions } from '../placement/usePlacementOptions.ts'
import OnboardingPageHeading from '../shared/OnboardingPageHeading.tsx'
import StudentPageLink from '../shared/StudentPageLink.tsx'
import RegistrationRequestsNotice from './RegistrationRequestsNotice.tsx'
import SingleRegistrationWorkflow from './SingleRegistrationWorkflow.tsx'
import { useSingleRegistration } from './useSingleRegistration.ts'

/** Students › Add Student: register one student, then follow their setup invitation below. */
export default function AddStudentPage({
  accessToken,
  identity,
  canReview,
}: {
  accessToken: string
  identity: string
  canReview: boolean
}) {
  const registration = useSingleRegistration(accessToken, identity)
  const placement = usePlacementOptions(accessToken, identity, true, registration.sectionId)
  const invitations = useStudentInvitations(accessToken, identity, true)

  return (
    <section className="student-onboarding-dashboard" aria-label="Student registration">
      <OnboardingPageHeading
        trail={['Students', 'Add Student']}
        title="Add Student"
        description="Create a student account and email a secure password setup link."
        action={
          <StudentPageLink page="bulk" className="student-onboarding-secondary student-onboarding-link-button">
            <FileSpreadsheet size={17} aria-hidden="true" /> Import from spreadsheet
          </StudentPageLink>
        }
      />
      {canReview && <RegistrationRequestsNotice accessToken={accessToken} />}
      <SingleRegistrationWorkflow
        registration={registration}
        placement={placement}
        resending={invitations.busy}
        onResend={invitations.resend}
      />
      <section className="student-onboarding-records" aria-label="Pending invitations">
        <InvitationMetrics
          invitations={invitations.invitations}
          unavailable={invitations.loading || Boolean(invitations.error)}
        />
        <StudentInvitationList
          invitations={invitations.invitations}
          loading={invitations.loading}
          error={invitations.error}
          fetching={invitations.fetching}
          busy={invitations.busy || registration.busy}
          sectionId={registration.sectionId}
          onRefresh={invitations.refetch}
          onResend={(id) => void invitations.resend(id)}
          onReassign={(id) => void invitations.reassign(id, registration.sectionId)}
        />
      </section>
    </section>
  )
}
