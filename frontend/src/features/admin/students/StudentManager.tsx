import { useAuth } from '../../auth/session/AuthProvider.tsx'
import { usePermissions } from '../../auth/access/usePermissions.ts'
import type { StudentWorkspacePage } from '../adminNavigation.ts'
import AdminApprovals from './AdminApprovals.tsx'
import StudentDirectoryPage from './directory/StudentDirectoryPage.tsx'
import StudentOnboardingPage from '../student-onboarding/StudentOnboardingPage.tsx'
import './studentWorkspace.css'

/** Keep account approval distinct while presenting it beside admin onboarding. */
export default function StudentManager({ page = 'register' }: { page?: StudentWorkspacePage }) {
  const { accessToken, user } = useAuth()
  const { canAll } = usePermissions()
  if (!user?.institution_id || !accessToken) {
    return <p role="status">A verified institution session is required to review student accounts.</p>
  }
  const canRead = canAll('students.read')
  const canReview = canAll('students.read', 'students.approve', 'students.reject')
  const canManageOnboarding = canAll(
    'students.create',
    'students.approve',
    'students.update',
    'students.read',
    'courses.manage',
  )
  const canUpdateStudents = canAll('students.update')
  const canManageStudentPlacement = canUpdateStudents && canAll('courses.manage', 'courses.read', 'departments.read')
  const canDeleteStudents = canAll('students.delete')
  const canResendStudentInvitations = canAll('students.create')
  const identity = `${user.user_id}:${user.institution_id}`
  if (page === 'all') {
    if (!canRead) return <p role="status">Your account does not have permission to view students.</p>
    return (
      <StudentDirectoryPage
        key={identity}
        accessToken={accessToken}
        identity={identity}
        canUpdateStudents={canUpdateStudents}
        canManageStudentPlacement={canManageStudentPlacement}
        canDeleteStudents={canDeleteStudents}
        canResendInvitations={canResendStudentInvitations}
      />
    )
  }
  if (page === 'requests') {
    if (!canReview) return <p role="status">Your account does not have permission to review student requests.</p>
    return <AdminApprovals key={identity} accessToken={accessToken} />
  }
  if (!canReview && !canManageOnboarding) {
    return <p role="status">Your account does not have permission to manage student accounts.</p>
  }
  if (!canManageOnboarding) return <AdminApprovals accessToken={accessToken} />
  return (
    <StudentOnboardingPage
      key={`${identity}:${page}`}
      accessToken={accessToken}
      identity={identity}
      canManage={canManageOnboarding}
      canReview={canReview}
      bulkOnly={page === 'bulk'}
    />
  )
}
