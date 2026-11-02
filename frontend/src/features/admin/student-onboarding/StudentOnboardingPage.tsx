import { useStudentOnboarding } from './useStudentOnboarding.ts'
import StudentOnboardingDashboard from './StudentOnboardingDashboard.tsx'
import StudentRegistrationWorkflow from './registration/StudentRegistrationWorkflow.tsx'
import './studentOnboarding.css'

export default function StudentOnboardingPage({
  accessToken,
  identity,
  canManage,
  canReview = false,
  bulkOnly = false,
}: {
  accessToken: string
  identity: string
  canManage: boolean
  canReview?: boolean
  bulkOnly?: boolean
}) {
  const model = useStudentOnboarding(accessToken, identity, canManage, bulkOnly ? 'bulk' : 'single')
  if (!canManage) {
    return (
      <p role="status">Student creation requires Students create/approve/update/read and Courses manage permissions.</p>
    )
  }
  return (
    <StudentOnboardingDashboard
      accessToken={accessToken}
      canReview={canReview}
      invitations={model.invitations.data?.invitations ?? []}
      invitationsLoading={model.invitations.isPending}
      invitationsError={model.invitations.error instanceof Error ? model.invitations.error.message : ''}
      invitationsFetching={model.invitations.isFetching}
      busy={model.busy}
      sectionId={model.sectionId}
      bulkOnly={bulkOnly}
      bulkStep={model.bulkStep}
      onRefresh={() => void model.invitations.refetch()}
      onResend={(id) => void model.resend(id)}
      onReassign={(id) => void model.reassign(id)}
    >
      <StudentRegistrationWorkflow model={model} bulkOnly={bulkOnly} />
    </StudentOnboardingDashboard>
  )
}
