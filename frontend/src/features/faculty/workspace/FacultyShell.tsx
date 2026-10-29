import { Bell, BookOpen, Bot, UserCircle, type LucideIcon } from 'lucide-react'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import ChatShell from '../../chat/ChatShell.tsx'
import LearningResourcesPage from '../../learning-resources/LearningResourcesPage.tsx'
import WorkspaceFrame from '../../workspace/WorkspaceFrame.tsx'
import WorkspacePageHeader from '../../workspace/WorkspacePageHeader.tsx'
import FacultyProfile from '../profile/FacultyProfile.tsx'
import FacultyComingSoon from './FacultyComingSoon.tsx'
import {
  buildFacultyNavigation,
  FACULTY_COMING_SOON_VIEWS,
  FACULTY_VIEW_HEADINGS,
  type FacultyView,
} from './facultyNavigation.ts'
import { FACULTY_PATHS, resolveFacultyRoute } from './facultyRoutes.ts'
import { navigateTo, useBrowserLocation } from '../../../lib/navigation.ts'

const icons: Record<FacultyView, LucideIcon> = {
  profile: UserCircle,
  notices: Bell,
  resources: BookOpen,
  assistant: Bot,
}
export default function FacultyShell() {
  const { user, role, logout } = useAuth()
  const { pathname } = useBrowserLocation()
  const navigation = buildFacultyNavigation(role, user?.effective_permissions)
  const route = resolveFacultyRoute(pathname)
  const view = route && navigation.some((item) => item.key === route.view) ? route.view : navigation[0]?.key
  const navigate = (next: FacultyView) => navigateTo(FACULTY_PATHS[next])
  if (!user || role !== 'faculty') return <main role="status">Faculty access is unavailable.</main>
  return (
    <WorkspaceFrame<FacultyView>
      navigation={navigation}
      currentView={view ?? 'profile'}
      icons={icons}
      onNavigate={navigate}
      panelLabel="Faculty Portal"
      navigationLabel="Faculty navigation"
      identityLabel={user.email?.trim() || 'Faculty'}
      identityRole="Faculty"
      onLogout={logout}
      onProfile={navigation.some((item) => item.key === 'profile') ? () => navigate('profile') : undefined}
    >
      {view ? (
        <>
          {view !== 'assistant' && view !== 'resources' && (
            <WorkspacePageHeader
              title={FACULTY_VIEW_HEADINGS[view]}
              description="Your faculty workspace and institution information."
            />
          )}
          {view === 'profile' && <FacultyProfile user={user} />}
          {view === 'resources' && <LearningResourcesPage />}
          {FACULTY_COMING_SOON_VIEWS.includes(view) && <FacultyComingSoon view={view} />}
          {view === 'assistant' && (
            <section aria-label="AI Assistant">
              <ChatShell />
            </section>
          )}
        </>
      ) : (
        <p role="status">Your account has no available faculty views.</p>
      )}
    </WorkspaceFrame>
  )
}
