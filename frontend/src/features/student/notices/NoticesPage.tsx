import { getMyNotices } from '../../../services/students/studentApi.ts'
import { useStudentResource } from '../shared/useStudentResource.ts'
import { SectionCard } from '../shared/SectionState.tsx'
import NoticesPanel from './NoticesPanel.tsx'

/**
 * Phase 6.16.3 — Notices page. Requests the backend's maximum notice page
 * (`student_notices.MAX_NOTICE_LIMIT === 20`), so the UI never asks for a
 * value outside the documented bounds. The endpoint is a bounded recent set —
 * pinned first, then newest — and its contract has NO pagination or category
 * filter parameters, so the page deliberately adds neither. Ordering and the
 * limit are server-authoritative; the panel renders every row the backend
 * returned, and content is plain text rendered as React text (never HTML).
 */
export function NoticesPage() {
  const notices = useStudentResource((token) => getMyNotices(token, 20), 'Unable to load notices.', '', 'notices-20')
  return (
    <SectionCard title="Notices from your institution" headingId="student-page-notices">
      <NoticesPanel notices={notices} />
    </SectionCard>
  )
}
