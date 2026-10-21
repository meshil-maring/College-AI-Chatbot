/**
 * Phase Admin-4 / Phase 6.19 — Admin shell.
 *
 * The administrative application shell. Navigation (navigation model,
 * fail-closed role gating, per-view headings) is defined in
 * `adminNavigation.ts`, derived exclusively from the server-authoritative
 * role held in AuthProvider state (`/auth/me` -> `user.role`, Phase 6.15.4).
 * This shell does NOT probe GET /admin/me for identity or role: the canonical
 * identity comes from the same AuthProvider state, so one authenticated
 * request bootstraps everything. Authorization itself remains fully
 * backend-enforced: every admin API request still carries the bearer token
 * and /admin/* endpoints reject non-admin tokens with 403.
 *
 * Phase 6.19 additions — all exposures of EXISTING verified contracts, no
 * new backend surface:
 *   - "Student Approvals" reuses the Phase 6.4 approval-queue contract
 *     (the same one the Phase 6.18 staff shell uses);
 *   - "AI Assistant" reuses the existing ChatShell (the authenticated chat
 *     contracts are `get_current_user`-authorized, so admin is allowed);
 *   - "Profile" renders the safe /auth/me identity fields.
 *
 * Session expiry is inherited, never duplicated: every request goes through
 * the shared API client (requestJson -> 401 -> notifySessionExpired ->
 * AuthProvider).
 *
 * Phase 6.20 — responsive/overflow parity with the student/faculty/staff
 * shells: the shell root clips accidental page-level horizontal overflow
 * (`overflow-x-clip`) and the header row can shrink (`min-w-0`). No visual
 * system was redesigned.
 */

import { useState } from 'react'
import AcademicSetup from './academic-setup/AcademicSetup.tsx'
import AdminFrame from './AdminFrame.tsx'
import { leaveStudents, navigateStudents, useStudentsLocation } from '../students/studentsNavigation.ts'
import {
  Bell,
  Bot,
  CalendarCheck,
  CircleHelp,
  ClipboardCheck,
  ClipboardList,
  FileText,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Settings,
  ShieldCheck,
  UserCheck,
  UserCircle,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { useAuth } from '../auth/session/AuthProvider.tsx'
import { usePermissions } from '../auth/access/usePermissions.ts'
import ChatShell from '../chat/ChatShell.tsx'
import AdminDashboard from './dashboard/AdminDashboard.tsx'
import AdminProfile from './profile/AdminProfile.tsx'
import FaqManager from './faqs/FaqManager.tsx'
import DocumentManager from './documents/DocumentManager.tsx'
import NoticeManager from './notices/NoticeManager.tsx'
import StudentManager from './students/StudentManager.tsx'
import ResultsManager from './results/ResultsManager.tsx'
import TestResultsManager from './test-results/TestResultsManager.tsx'
import AttendanceManager from './attendance/AttendanceManager.tsx'
import StaffFacultyManager from './staff-faculty/StaffFacultyManager.tsx'
import StaffPermissionManager from './permissions/StaffPermissionManager.tsx'
import FacultyAssignmentManager from './faculty-assignments/FacultyAssignmentManager.tsx'
import { ADMIN_VIEW_HEADINGS, buildAdminNavigation, type AdminView } from './adminNavigation.ts'

const ADMIN_NAV_ICONS: Record<AdminView, LucideIcon> = {
  dashboard: LayoutDashboard,
  approvals: UserCheck,
  'staff-faculty': Users,
  students: Users,
  attendance: CalendarCheck,
  results: ClipboardCheck,
  'test-results': ClipboardList,
  notices: Bell,
  documents: FileText,
  faqs: CircleHelp,
  assistant: Bot,
  profile: UserCircle,
  permissions: ShieldCheck,
  'faculty-assignments': Settings,
  'academic-setup': GraduationCap,
}

export default function AdminShell() {
  const { user, role, accessToken, logout } = useAuth()
  const [workspaceView, setWorkspaceView] = useState<AdminView>('dashboard')
  const studentsLocation = useStudentsLocation('admin')
  const currentView = studentsLocation ? 'students' : workspaceView
  const studentSection = studentsLocation?.page ?? 'roster'
  const navigation = buildAdminNavigation(role, user?.effective_permissions)
  const [studentSearch, setStudentSearch] = useState('')
  const { can, canAll } = usePermissions()
  const canReviewStudents = canAll('students.read', 'students.approve', 'students.reject')
  const canBrowseStudents = canAll('students.read', 'attendance.read')

  function setCurrentView(view: AdminView) {
    if (view === 'students' || view === 'approvals') navigateStudents('admin', view === 'approvals' ? 'waiting-approval' : 'roster')
    else { setWorkspaceView(view); leaveStudents() }
  }

  // Phase 6.15.4 — identity comes from the canonical /auth/me bootstrap
  // (AuthProvider state). App.tsx only renders this shell once /auth/me has
  // resolved the authenticated identity, so `user` is present.
  const identityLabel = user?.email?.trim() || 'Admin'

  return (
    <AdminFrame
      navigation={navigation}
      currentView={currentView}
      icons={ADMIN_NAV_ICONS}
      onNavigate={setCurrentView}
      studentSection={studentSection}
      onStudentSection={(section) => navigateStudents('admin', section, 'individual', studentsLocation?.sectionId)}
      studentSectionId={studentsLocation?.sectionId}
      canReviewStudents={canReviewStudents || canBrowseStudents}
      canReadStudentHistory={canBrowseStudents}
      canRegisterStudents={can('students', 'create')}
      identityLabel={identityLabel}
      onLogout={logout}
      onSearch={(search) => { setStudentSearch(search); navigateStudents('admin', 'roster') }}
    >
        {user === null ? (
          <section
            role="status"
            className="rounded-2xl border border-slate-700 bg-slate-800 p-8 text-center"
          >
            <h1 className="text-2xl font-bold text-white">Admin workspace unavailable</h1>
            <p className="mt-3 text-sm text-slate-300">
              Your administrator identity could not be loaded. Please sign in again.
            </p>
            <button
              type="button"
              onClick={logout}
              className="mt-6 inline-flex items-center gap-2 rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-400"
            >
              <LogOut aria-hidden="true" className="h-4 w-4" />
              Sign out
            </button>
          </section>
        ) : !navigation.some((item) => item.key === currentView) ? (
          <section
            role="status"
            className="rounded-2xl border border-slate-700 bg-slate-800 p-8 text-center"
          >
            <h1 className="text-2xl font-bold text-white">No available admin views</h1>
            <p className="mt-3 text-sm text-slate-300">
              Your account has no permissions for the selected administrative view.
            </p>
          </section>
        ) : (
          <>
            {currentView !== 'assistant' && currentView !== 'faculty-assignments' && currentView !== 'students' && currentView !== 'approvals' ? (
              <h1 className="mb-4 break-words text-2xl font-bold text-white">
                {ADMIN_VIEW_HEADINGS[currentView]}
              </h1>
            ) : null}
            {currentView === 'dashboard' ? (
              // Phase 7.21 — the dashboard's quick actions switch to EXISTING
              // admin views through the same `currentView` state the header
              // navigation already uses. No new screen, no second dashboard.
              <AdminDashboard onNavigate={setCurrentView} />
            ) : null}

            {currentView === 'staff-faculty' ? (
              accessToken !== null ? (
                <StaffFacultyManager accessToken={accessToken} />
              ) : (
                <section role="status" className="rounded-2xl border border-slate-700 bg-slate-800 p-8 text-center">
                  <p className="text-sm text-slate-300">Your session could not be verified. Please sign in again.</p>
                </section>
              )
            ) : null}
            {currentView === 'permissions' && accessToken !== null ? (
              <StaffPermissionManager accessToken={accessToken} />
            ) : null}
            {currentView === 'faculty-assignments' && accessToken !== null ? (
              <FacultyAssignmentManager accessToken={accessToken} />
            ) : null}
            {currentView === 'students' ? <StudentManager key={`${accessToken}:${user.institution_id}`} section={studentSection} search={studentSearch} sectionId={studentsLocation?.sectionId ?? ''} onNavigate={(page, id, replace) => navigateStudents('admin', page, page === 'register' ? studentsLocation?.method : 'individual', id, replace)} registrationMethod={studentsLocation?.method ?? 'individual'} onRegistrationMethod={(method) => navigateStudents('admin', 'register', method, studentsLocation?.sectionId)} /> : null}
            {currentView === 'academic-setup' && accessToken !== null ? <AcademicSetup accessToken={accessToken} /> : null}
            {currentView === 'attendance' ? <AttendanceManager /> : null}
            {currentView === 'results' ? <ResultsManager /> : null}
            {currentView === 'test-results' ? <TestResultsManager /> : null}
            {currentView === 'notices' ? <NoticeManager /> : null}
            {currentView === 'documents' ? <DocumentManager /> : null}
            {currentView === 'faqs' ? <FaqManager /> : null}
            {currentView === 'assistant' ? (
              <section aria-label="AI Assistant">
                <ChatShell />
              </section>
            ) : null}
            {currentView === 'profile' ? <AdminProfile user={user} /> : null}
          </>
        )}
    </AdminFrame>
  )
}
