import { useAuth } from '../../auth/session/AuthProvider.tsx'
import { usePermissions } from '../../auth/access/usePermissions.ts'
import AdminApprovals from './AdminApprovals.tsx'

/** Student account decisions remain separate from the retired academic roster workflow. */
export default function StudentManager() {
  const { accessToken, user } = useAuth()
  const { canAll } = usePermissions()
  if (!user?.institution_id || !accessToken) {
    return <p role="status">A verified institution session is required to review student accounts.</p>
  }
  if (!canAll('students.read', 'students.approve', 'students.reject')) {
    return <p role="status">Your account does not have permission to review student accounts.</p>
  }
  return <AdminApprovals accessToken={accessToken} />
}
