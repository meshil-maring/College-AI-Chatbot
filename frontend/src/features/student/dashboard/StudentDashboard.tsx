/**
 * Student dashboard: a read-only overview composed from existing student
 * APIs. Widgets without a backend API (attendance, CGPA, timetable,
 * deadlines) are labelled "Coming soon" rather than showing invented data.
 */

import type { StudentNavItem, StudentView } from '../workspace/studentNavigation.ts'
import DashboardHeader from './DashboardHeader.tsx'
import DashboardStats from './DashboardStats.tsx'
import { SubjectAttendance, TodaySchedule, UpcomingDeadlines } from './ComingSoonPanels.tsx'
import OngoingRequests from './OngoingRequests.tsx'
import RecentNotices from './RecentNotices.tsx'
import { useDashboardData } from './useDashboardData.ts'

export default function StudentDashboard({
  navigation,
  onNavigate,
}: {
  navigation: readonly StudentNavItem[]
  onNavigate: (view: StudentView) => void
}) {
  const can = (view: StudentView) => navigation.some((item) => item.key === view)
  const { semester, openTransfers } = useDashboardData(can('registration'), can('transfer-requests'))
  return (
    <div className="space-y-5">
      <DashboardHeader semester={semester} />
      <DashboardStats semester={semester} />
      <div className="grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
        <TodaySchedule />
        <RecentNotices enabled={can('notices')} onViewAll={() => onNavigate('notices')} />
        <div className="space-y-5 lg:col-span-2 xl:col-span-1">
          <UpcomingDeadlines />
          <SubjectAttendance semester={semester.data} />
          <OngoingRequests requests={openTransfers} onViewAll={() => onNavigate('transfer-requests')} />
        </div>
      </div>
    </div>
  )
}
