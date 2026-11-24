import { ClipboardCheck } from 'lucide-react'
import { useApiQuery } from '../../../../hooks/useApiQuery.ts'
import { listPendingStudents } from '../../../../services/admin/adminApi.ts'
import StudentPageLink from '../shared/StudentPageLink.tsx'

/**
 * Points to the Registration Requests page when self-registered students are waiting.
 * Shares the approval queue's cache key, so opening the page does not refetch.
 */
export default function RegistrationRequestsNotice({ accessToken }: { accessToken: string }) {
  const queue = useApiQuery(['admin', 'pending-students', accessToken], () => listPendingStudents(accessToken))
  const waiting = Array.isArray(queue.data) ? queue.data.length : 0
  if (!waiting) return null
  return (
    <aside className="student-onboarding-requests-notice" aria-label="Registration requests">
      <ClipboardCheck size={18} aria-hidden="true" />
      <p>
        <strong>
          {waiting} self-registration request{waiting === 1 ? '' : 's'}
        </strong>{' '}
        {waiting === 1 ? 'is' : 'are'} waiting for review.
      </p>
      <StudentPageLink page="requests">
        Review requests <span aria-hidden="true">→</span>
      </StudentPageLink>
    </aside>
  )
}
