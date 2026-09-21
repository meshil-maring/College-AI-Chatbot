/** Phase 6.16.2 — Full student pages (read-only, one resource per page). */

import {
  getMyAcademicProfile,
  getMyNotices,
  getMyResources,
} from '../../services/studentApi.ts'
import { useStudentResource } from './useStudentResource.ts'
import { SectionCard } from './SectionState.tsx'
import StudentIdentityCard from './StudentIdentityCard.tsx'
import AcademicContextCard from './AcademicContextCard.tsx'
import { AttendanceDetailPage } from './AttendanceDetail.tsx'
import { ResultsDetailPage } from './ResultsDetail.tsx'
import NoticesPanel from './NoticesPanel.tsx'
import ResourcesPanel from './ResourcesPanel.tsx'

/**
 * Phase 6.16.2 — the Attendance and Results pages are the full detail
 * experiences (academic context + summary + filters + records), built in
 * `AttendanceDetail.tsx` / `ResultsDetail.tsx` over the existing read-only
 * contracts. The dashboard keeps using the compact panels.
 */
export function AttendancePage() {
  return <AttendanceDetailPage />
}

export function ResultsPage() {
  return <ResultsDetailPage />
}

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
  const notices = useStudentResource((token) => getMyNotices(token, 20), 'Unable to load notices.')
  return (
    <SectionCard title="Notices from your institution" headingId="student-page-notices">
      <NoticesPanel notices={notices} />
    </SectionCard>
  )
}

/**
 * Phase 6.16.3 — Learning Resources page. `20` stays well inside the backend's
 * resource limit contract (`student_resources.MAX_RESOURCE_LIMIT === 50`).
 * The endpoint returns safe metadata only — there is NO storage-access or
 * download contract — so the page renders metadata without any open/link
 * action, and adds no source-type filter the backend does not support (the
 * endpoint's only query field is `limit`).
 */
export function ResourcesPage() {
  const resources = useStudentResource((token) => getMyResources(token, 20), 'Unable to load learning resources.')
  return (
    <SectionCard title="Learning resources" headingId="student-page-resources">
      <ResourcesPanel resources={resources} />
    </SectionCard>
  )
}

/**
 * Phase 6.16.3 — Profile page (READ-ONLY BY DESIGN). The backend exposes NO
 * student-owned profile-update contract (every `PATCH /students/*` route is
 * admin-only), so no edit UI exists here and none was invented. Identity and
 * academic context come from the single `GET /students/me/academic-profile`
 * request, shared by both cards below — one request per profile mount.
 */
export function ProfilePage() {
  const profile = useStudentResource(getMyAcademicProfile, 'Unable to load your academic profile.')
  return (
    <div className="space-y-4">
      <SectionCard title="Your profile" headingId="student-page-profile">
        <StudentIdentityCard profile={profile} />
      </SectionCard>
      <SectionCard title="Academic context" headingId="student-page-context">
        <AcademicContextCard profile={profile} />
      </SectionCard>
    </div>
  )
}

