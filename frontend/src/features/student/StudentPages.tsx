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

export function NoticesPage() {
  const notices = useStudentResource((token) => getMyNotices(token, 20), 'Unable to load notices.')
  return (
    <SectionCard title="Notices from your institution" headingId="student-page-notices">
      <NoticesPanel notices={notices} />
    </SectionCard>
  )
}

export function ResourcesPage() {
  const resources = useStudentResource((token) => getMyResources(token, 20), 'Unable to load learning resources.')
  return (
    <SectionCard title="Learning resources" headingId="student-page-resources">
      <ResourcesPanel resources={resources} />
    </SectionCard>
  )
}

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
