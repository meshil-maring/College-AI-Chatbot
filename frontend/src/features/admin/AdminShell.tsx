import { useState } from 'react'
import { Bell, BookOpen, Bot, FileText, ShieldCheck, UserCircle, Users, type LucideIcon } from 'lucide-react'
import { useAuth } from '../auth/session/AuthProvider.tsx'
import AdminFrame from './AdminFrame.tsx'
import AdminProfile from './profile/AdminProfile.tsx'
import AcademicWorkspace from './academic-setup/overview/AcademicWorkspace.tsx'
import type { AcademicPage } from './academic-setup/overview/academicOverviewModel.ts'
import StudentManager from './students/StudentManager.tsx'
import StaffFacultyManager from './staff-faculty/StaffFacultyManager.tsx'
import StaffPermissionManager from './permissions/StaffPermissionManager.tsx'
import NoticeManager from './notices/NoticeManager.tsx'
import LearningResourcesPage from '../learning-resources/LearningResourcesPage.tsx'
import FaqManager from './faqs/FaqManager.tsx'
import ChatShell from '../chat/ChatShell.tsx'
import { ADMIN_VIEW_HEADINGS, buildAdminNavigation, type AdminView } from './adminNavigation.ts'
import WorkspacePageHeader from '../workspace/WorkspacePageHeader.tsx'

const descriptions: Partial<Record<AdminView, string>> = {
  profile: 'Your administrator identity and institution details.',
  'staff-faculty': 'Review membership requests and manage your institution’s staff and faculty accounts.',
  approvals: 'Review student registration requests for your institution.',
  notices: 'Create and manage information shared with your institution.',
  documents: 'Manage the documents and knowledge sources used by your institution’s AI.',
  faqs: 'Maintain clear answers to frequently asked questions.',
  permissions: 'Manage the access granted to staff in your institution.',
}

const icons: Record<AdminView, LucideIcon> = {
  profile: UserCircle,
  'academic-setup': BookOpen,
  'staff-faculty': Users,
  approvals: Users,
  notices: Bell,
  documents: FileText,
  faqs: BookOpen,
  assistant: Bot,
  permissions: ShieldCheck,
}
export default function AdminShell() {
  const { user, role, accessToken, logout } = useAuth()
  const [selected, setSelected] = useState<AdminView>('profile')
  const [academicPage, setAcademicPage] = useState<AcademicPage>('overview')
  const [academicSearch, setAcademicSearch] = useState('')
  const navigation = buildAdminNavigation(role, user?.effective_permissions)
  const view = navigation.some((item) => item.key === selected) ? selected : navigation[0]?.key
  if (!user || role !== 'admin') return <main role="status">Administrator access is unavailable.</main>
  return (
    <AdminFrame
      navigation={navigation}
      currentView={view ?? 'profile'}
      icons={icons}
      onNavigate={setSelected}
      identityLabel={user.email?.trim() || 'Administrator'}
      onLogout={logout}
      academicPage={academicPage}
      onAcademicNavigate={(page) => {
        setAcademicPage(page)
        setAcademicSearch('')
      }}
      academicSearch={academicSearch}
      onAcademicSearch={(value) => {
        setAcademicSearch(value)
        setAcademicPage('overview')
      }}
    >
      {view ? (
        <>
          {view !== 'assistant' && view !== 'academic-setup' && view !== 'documents' && (
            <WorkspacePageHeader title={ADMIN_VIEW_HEADINGS[view]} description={descriptions[view]} />
          )}
          {view === 'profile' && <AdminProfile user={user} />}
          {view === 'academic-setup' && (
            <AcademicWorkspace
              page={academicPage}
              search={academicSearch}
              onNavigate={setAcademicPage}
              onClearSearch={() => setAcademicSearch('')}
            />
          )}
          {view === 'staff-faculty' && accessToken && <StaffFacultyManager accessToken={accessToken} />}
          {view === 'approvals' && <StudentManager />}
          {view === 'notices' && <NoticeManager />}
          {view === 'documents' && <LearningResourcesPage />}
          {view === 'faqs' && <FaqManager />}
          {view === 'permissions' && accessToken && <StaffPermissionManager accessToken={accessToken} />}
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
