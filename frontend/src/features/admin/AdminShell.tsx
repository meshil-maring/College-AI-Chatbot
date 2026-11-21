import {
  Bell,
  Bot,
  BriefcaseBusiness,
  CircleHelp,
  FileText,
  School,
  UserCircle,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { hasPermission } from '../auth/access/permissions.ts'
import { useAuth } from '../auth/session/AuthProvider.tsx'
import AdminFrame from './AdminFrame.tsx'
import AdminProfile from './profile/AdminProfile.tsx'
import AcademicWorkspace from './academic-setup/overview/AcademicWorkspace.tsx'
import StudentManager from './students/StudentManager.tsx'
import StaffFacultyManager from './staff-faculty/StaffFacultyManager.tsx'
import { STAFF_FACULTY_PAGE_INFO } from './staff-faculty/StaffFacultyNavigation.tsx'
import NoticeManager from './notices/NoticeManager.tsx'
import LearningResourcesPage from '../learning-resources/LearningResourcesPage.tsx'
import FaqManager from './faqs/FaqManager.tsx'
import ChatShell from '../chat/ChatShell.tsx'
import { ADMIN_VIEW_HEADINGS, buildAdminNavigation, type AdminView } from './adminNavigation.ts'
import WorkspacePageHeader from '../workspace/WorkspacePageHeader.tsx'
import { useAdminWorkspaceNavigation } from './navigation/useAdminWorkspaceNavigation.ts'

const descriptions: Partial<Record<AdminView, string>> = {
  profile: 'Your administrator identity and institution details.',
  'staff-faculty':
    'Approve staff and faculty into a department, keep their departments up to date and give staff extra permissions.',
  approvals: 'Register students, send secure account setup links, and review self-registration requests.',
  notices: 'Create and manage information shared with your institution.',
  documents: 'Manage the documents and knowledge sources used by your institution’s AI.',
  faqs: 'Maintain clear answers to frequently asked questions.',
}

const icons: Record<AdminView, LucideIcon> = {
  profile: UserCircle,
  // One distinct icon per destination so the collapsed rail stays readable.
  'academic-setup': School,
  'staff-faculty': BriefcaseBusiness,
  approvals: Users,
  notices: Bell,
  documents: FileText,
  faqs: CircleHelp,
  assistant: Bot,
}
export default function AdminShell() {
  const { user, role, accessToken, logout } = useAuth()
  const {
    selected,
    academicPage,
    academicSearch,
    navigateView,
    navigateAcademic,
    searchAcademic,
    clearAcademicSearch,
    studentPage,
    navigateStudentPage,
    staffPage: requestedStaffPage,
    navigateStaffPage,
  } = useAdminWorkspaceNavigation(
    user ? JSON.stringify([user.auth_user_id ?? user.user_id, user.institution_id]) : undefined,
  )
  const navigation = buildAdminNavigation(role, user?.effective_permissions)
  const view = navigation.some((item) => item.key === selected) ? selected : navigation[0]?.key
  if (!user || role !== 'admin') return <main role="status">Administrator access is unavailable.</main>
  // Presentation only; the permissions API enforces `permissions.read` either way.
  const canManagePermissions =
    user.effective_permissions === undefined || hasPermission(user.effective_permissions, 'permissions.read')
  const staffPage = requestedStaffPage === 'permissions' && !canManagePermissions ? 'requests' : requestedStaffPage
  return (
    <AdminFrame
      navigation={navigation}
      currentView={view ?? 'profile'}
      icons={icons}
      onNavigate={navigateView}
      identityLabel={user.email?.trim() || 'Administrator'}
      onLogout={logout}
      academicPage={academicPage}
      onAcademicNavigate={navigateAcademic}
      academicSearch={academicSearch}
      onAcademicSearch={searchAcademic}
      studentPage={studentPage}
      onStudentNavigate={navigateStudentPage}
      staffPage={staffPage}
      onStaffNavigate={navigateStaffPage}
      canManagePermissions={canManagePermissions}
    >
      {view ? (
        <>
          {view !== 'assistant' && view !== 'academic-setup' && view !== 'documents' && view !== 'approvals' && (
            <WorkspacePageHeader
              title={view === 'staff-faculty' ? STAFF_FACULTY_PAGE_INFO[staffPage].label : ADMIN_VIEW_HEADINGS[view]}
              eyebrow={view === 'staff-faculty' ? ADMIN_VIEW_HEADINGS[view] : undefined}
              description={
                view === 'staff-faculty' ? STAFF_FACULTY_PAGE_INFO[staffPage].description : descriptions[view]
              }
            />
          )}
          {view === 'profile' && <AdminProfile user={user} />}
          {view === 'academic-setup' && (
            <AcademicWorkspace
              page={academicPage}
              search={academicSearch}
              onNavigate={navigateAcademic}
              onClearSearch={clearAcademicSearch}
            />
          )}
          {view === 'staff-faculty' && accessToken && (
            <StaffFacultyManager
              accessToken={accessToken}
              page={staffPage}
              onNavigate={navigateStaffPage}
              canManagePermissions={canManagePermissions}
            />
          )}
          {view === 'approvals' && <StudentManager page={studentPage} />}
          {view === 'notices' && <NoticeManager />}
          {view === 'documents' && <LearningResourcesPage />}
          {view === 'faqs' && <FaqManager />}
          {view === 'assistant' && (
            <section aria-label="AI Assistant">
              <ChatShell />
            </section>
          )}
        </>
      ) : (
        <p role="status">Your account has no available administration views.</p>
      )}
    </AdminFrame>
  )
}
