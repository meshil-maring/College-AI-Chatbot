/** Phase 6.16 — Student dashboard overview (concise, read-only). */

import {
  getMyAcademicProfile,
  getMyAttendanceSummary,
  getMyNotices,
  getMyResources,
  getMyResultsSummary,
  getMyTestResultsSummary,
} from '../../../services/students/studentApi.ts'
import type { StudentView } from '../workspace/studentNavigation.ts'
import { useStudentResource } from '../shared/useStudentResource.ts'
import type { StudentResourceState } from '../shared/useStudentResource.ts'
import type { StudentAcademicProfile } from '../../../types/student.ts'
import { SectionCard } from '../shared/SectionState.tsx'
import StudentIdentityCard from '../profile/StudentIdentityCard.tsx'
import AcademicContextCard from '../shared/AcademicContextCard.tsx'
import AttendancePanel from '../attendance/AttendancePanel.tsx'
import ResultsPanel from '../results/ResultsPanel.tsx'
import NoticesPanel from '../notices/NoticesPanel.tsx'
import ResourcesPanel from '../resources/ResourcesPanel.tsx'

function ViewLink({ label, view, onNavigate }: { label: string; view: StudentView; onNavigate: (view: StudentView) => void }) {
  return (
    <button
      type="button"
      onClick={() => onNavigate(view)}
      aria-label={label}
      className="max-w-full truncate rounded-lg px-2 py-1 text-xs font-medium text-emerald-300 hover:bg-emerald-500/10 focus:outline-none focus:ring-2 focus:ring-emerald-400"
    >
      {label}
    </button>
  )
}

export default function StudentDashboard({ onNavigate }: { onNavigate: (view: StudentView) => void }) {
  const profile = useStudentResource(getMyAcademicProfile, 'Unable to load your academic profile.', '', 'academic-profile')
  return <StudentDashboardContent profile={profile} onNavigate={onNavigate} />
}

/** The shell reuses its access-check profile instead of requesting it twice. */
export function StudentDashboardContent({ profile, onNavigate }: {
  profile: StudentResourceState<StudentAcademicProfile>
  onNavigate: (view: StudentView) => void
}) {
  const attendance = useStudentResource(getMyAttendanceSummary, 'Unable to load attendance.', '', 'attendance-summary')
  const results = useStudentResource(getMyResultsSummary, 'Unable to load results.', '', 'results-summary')
  const testResults = useStudentResource(getMyTestResultsSummary, 'Unable to load results.', '', 'test-results-summary')
  const notices = useStudentResource((token) => getMyNotices(token, 5), 'Unable to load notices.', '', 'notices-5')
  const resources = useStudentResource((token) => getMyResources(token, 6), 'Unable to load learning resources.', '', 'resources-6')

  return (
    <div className="min-w-0 space-y-4 overflow-x-clip">
      <SectionCard title="Your profile" headingId="student-dashboard-profile">
        <StudentIdentityCard profile={profile} />
      </SectionCard>

      <SectionCard title="Academic context" headingId="student-dashboard-context">
        <AcademicContextCard profile={profile} />
      </SectionCard>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SectionCard
          title="Attendance overview"
          headingId="student-dashboard-attendance"
          action={<ViewLink label="View all attendance" view="attendance" onNavigate={onNavigate} />}
        >
          <AttendancePanel attendance={attendance} compact />
        </SectionCard>
        <SectionCard
          title="Results overview"
          headingId="student-dashboard-results"
          action={<ViewLink label="View all results" view="results" onNavigate={onNavigate} />}
        >
          <ResultsPanel results={results} testResults={testResults} compact />
        </SectionCard>
      </div>

      <SectionCard
        title="Recent notices"
        headingId="student-dashboard-notices"
        action={<ViewLink label="View all notices" view="notices" onNavigate={onNavigate} />}
      >
        <NoticesPanel notices={notices} compact />
      </SectionCard>

      <SectionCard
        title="Learning resources"
        headingId="student-dashboard-resources"
        action={<ViewLink label="View all resources" view="resources" onNavigate={onNavigate} />}
      >
        <ResourcesPanel resources={resources} compact />
      </SectionCard>

      <SectionCard title="Ask the AI Assistant" headingId="student-dashboard-assistant">
        <p className="break-words text-sm text-slate-300">
          Get answers about your college, academic resources, attendance, results, notices, and available knowledge.
        </p>
        <button
          type="button"
          onClick={() => onNavigate('assistant')}
          className="mt-3 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        >
          Open AI Assistant
        </button>
      </SectionCard>
    </div>
  )
}
