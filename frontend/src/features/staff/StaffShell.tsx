import { useState } from 'react'
import AcademicPackagesWorkspace from '../academic-packages/AcademicPackagesWorkspace.tsx'
import { Bot, LayoutDashboard, UserCircle, Users, type LucideIcon } from 'lucide-react'
import { useAuth } from '../auth/session/AuthProvider.tsx'
import { hasPermission } from '../auth/access/permissions.ts'
import ChatShell from '../chat/ChatShell.tsx'
import { STAFF_VIEW_HEADINGS, buildStaffNavigation, type StaffView } from './staffNavigation.ts'
import StaffApprovals from './StaffApprovals.tsx'
import StaffDashboard from './StaffDashboard.tsx'
import StaffProfile from './StaffProfile.tsx'
import { StudentsNavigation, StudentsPageHeader } from '../students/StudentsUI.tsx'
import WorkspaceFrame from '../workspace/WorkspaceFrame.tsx'
import { STUDENT_PAGES, leaveStudents, navigateStudents, studentsPageHref, useStudentsLocation } from '../students/studentsNavigation.ts'

const icons: Record<StaffView, LucideIcon> = { dashboard: LayoutDashboard, approvals: Users, assistant: Bot, profile: UserCircle, 'academic-packages': Users }

export default function StaffShell() {
  const { user, role, accessToken, logout } = useAuth()
  const [workspaceView, setWorkspaceView] = useState<StaffView>('dashboard')
  const studentsLocation = useStudentsLocation('staff')
  const view = studentsLocation ? 'approvals' : workspaceView
  const navigation = buildStaffNavigation(role, user?.effective_permissions)
  const permissions = user?.effective_permissions
  const displayName = user?.email?.trim() || 'Staff'
  function setView(next: StaffView) {
    if (next === 'approvals') navigateStudents('staff', 'waiting-approval')
    else { setWorkspaceView(next); leaveStudents() }
  }

  return <WorkspaceFrame<StaffView> navigation={navigation} currentView={view} icons={icons} onNavigate={setView}
    studentsView="approvals" studentsNavigationId="staff-students-pages"
    studentsNavigation={<StudentsNavigation id="staff-students-pages" active="waiting-approval" items={STUDENT_PAGES.filter((item) => item.key === 'waiting-approval').map((item) => ({ ...item, href: studentsPageHref('staff', item.key) }))} onNavigate={() => setView('approvals')} />}
    panelLabel="Staff Panel" navigationLabel="Staff navigation" identityLabel={displayName} identityRole="Staff" onLogout={logout}
    onProfile={navigation.some((item) => item.key === 'profile') ? () => setView('profile') : undefined}>
    {user === null ? <section className="students-empty" role="status"><h1>Staff workspace unavailable</h1><p>Your staff identity could not be loaded. Please sign in again.</p></section>
      : !navigation.some((item) => item.key === view) ? <section className="students-empty" role="status"><h1>No available views</h1><p>Your account has no permissions for the selected staff view.</p></section>
        : <>
          {view !== 'assistant' && view !== 'approvals' && <h1 className="mb-4 break-words text-2xl font-bold text-white">{STAFF_VIEW_HEADINGS[view]}</h1>}
          {view === 'dashboard' && <StaffDashboard user={user} onNavigate={setView} />}
          {view === 'approvals' && <section className="students-content students-scope">
            <StudentsPageHeader page="Waiting approval" title="Students" description="Review student registrations awaiting approval for your institution." />
            {accessToken ? <StaffApprovals accessToken={accessToken} canApprove={permissions === undefined || hasPermission(permissions, 'students.approve')} canReject={permissions === undefined || hasPermission(permissions, 'students.reject')} />
              : <p className="students-empty" role="status">Your session could not be verified. Please sign in again.</p>}
          </section>}
          {view === 'profile' && <StaffProfile user={user} />}
          {view === 'academic-packages' && accessToken && <AcademicPackagesWorkspace accessToken={accessToken} />}
          {view === 'assistant' && <section aria-label="AI Assistant"><ChatShell /></section>}
        </>}
  </WorkspaceFrame>
}
