import { useState } from 'react'
import { Bell, BookOpen, Bot, FileText, ShieldCheck, UserCircle, Users, type LucideIcon } from 'lucide-react'
import { useAuth } from '../auth/session/AuthProvider.tsx'
import AdminFrame from './AdminFrame.tsx'
import AdminProfile from './profile/AdminProfile.tsx'
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
    >
      {view ? (
        <>
          {view !== 'assistant' && <h1 className="mb-5 text-2xl font-bold text-white">{ADMIN_VIEW_HEADINGS[view]}</h1>}
          {view === 'profile' && <AdminProfile user={user} />}
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
