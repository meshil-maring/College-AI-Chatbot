/** Phase 6.16 — Full student pages (read-only, one resource per page). */

import {
  getMyAcademicProfile,
  getMyAttendanceSummary,
  getMyNotices,
  getMyResources,
  getMyResultsSummary,
  getMyTestResultsSummary,
} from '../../services/studentApi.ts'
import { useStudentResource } from './useStudentResource.ts'
import { SectionCard } from './SectionState.tsx'
import StudentIdentityCard from './StudentIdentityCard.tsx'
import AcademicContextCard from './AcademicContextCard.tsx'
import AttendancePanel from './AttendancePanel.tsx'
import ResultsPanel from './ResultsPanel.tsx'
import NoticesPanel from './NoticesPanel.tsx'
import ResourcesPanel from './ResourcesPanel.tsx'

export function AttendancePage() {
  const attendance = useStudentResource(getMyAttendanceSummary, 'Unable to load attendance.')
  return (
    <SectionCard title="Your attendance" headingId="student-page-attendance">
      <AttendancePanel attendance={attendance} />
    </SectionCard>
  )
}

export function ResultsPage() {
  const results = useStudentResource(getMyResultsSummary, 'Unable to load results.')
  const testResults = useStudentResource(getMyTestResultsSummary, 'Unable to load results.')
  return (
    <SectionCard title="Your results" headingId="student-page-results">
      <ResultsPanel results={results} testResults={testResults} />
    </SectionCard>
  )
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
