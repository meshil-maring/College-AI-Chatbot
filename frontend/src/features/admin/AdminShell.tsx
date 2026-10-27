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
import DocumentManager from './documents/DocumentManager.tsx'
import FaqManager from './faqs/FaqManager.tsx'
import ChatShell from '../chat/ChatShell.tsx'
import { ADMIN_VIEW_HEADINGS, buildAdminNavigation, type AdminView } from './adminNavigation.ts'

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
          {view !== 'assistant' && view !== 'academic-setup' && (
            <h1 className="mb-5 text-2xl font-bold text-white">{ADMIN_VIEW_HEADINGS[view]}</h1>
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
          {view === 'documents' && <DocumentManager />}
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
