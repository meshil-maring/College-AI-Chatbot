import { useState } from 'react'
import { Bot, UserCircle, Users, type LucideIcon } from 'lucide-react'
import { useAuth } from '../auth/session/AuthProvider.tsx'
import { hasPermission } from '../auth/access/permissions.ts'
import ChatShell from '../chat/ChatShell.tsx'
import StaffApprovals from './StaffApprovals.tsx'
import StaffProfile from './StaffProfile.tsx'
import { buildStaffNavigation, STAFF_VIEW_HEADINGS, type StaffView } from './staffNavigation.ts'
import WorkspaceFrame from '../workspace/WorkspaceFrame.tsx'
import WorkspacePageHeader from '../workspace/WorkspacePageHeader.tsx'

const icons: Record<StaffView, LucideIcon> = { approvals: Users, assistant: Bot, profile: UserCircle }
export default function StaffShell() {
  const { user, role, accessToken, logout } = useAuth()
  const [selected, setSelected] = useState<StaffView>('profile')
  const navigation = buildStaffNavigation(role, user?.effective_permissions)
  const view = navigation.some((item) => item.key === selected) ? selected : navigation[0]?.key
  if (!user || role !== 'staff') return <main role="status">Staff access is unavailable.</main>
  return (
    <WorkspaceFrame<StaffView>
      navigation={navigation}
      currentView={view ?? 'profile'}
      icons={icons}
      onNavigate={setSelected}
      panelLabel="Staff Panel"
      navigationLabel="Staff navigation"
      identityLabel={user.email?.trim() || 'Staff'}
      identityRole="Staff"
      onLogout={logout}
      onProfile={navigation.some((item) => item.key === 'profile') ? () => setSelected('profile') : undefined}
    >
      {view ? (
        <>
          {view !== 'assistant' && (
            <WorkspacePageHeader
              title={STAFF_VIEW_HEADINGS[view]}
              description={
                view === 'profile'
                  ? 'Your staff identity and institution details.'
                  : 'Review student registration requests for your institution.'
              }
            />
          )}
          {view === 'profile' && <StaffProfile user={user} />}
          {view === 'approvals' && accessToken && (
            <StaffApprovals
              accessToken={accessToken}
              canApprove={hasPermission(user.effective_permissions ?? [], 'students.approve')}
              canReject={hasPermission(user.effective_permissions ?? [], 'students.reject')}
            />
          )}
          {view === 'assistant' && (
            <section aria-label="AI Assistant">
              <ChatShell />
            </section>
          )}
        </>
      ) : (
        <p role="status">Your account has no available staff views.</p>
      )}
    </WorkspaceFrame>
  )
}
