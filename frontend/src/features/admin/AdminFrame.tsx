import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import type { AdminNavItem, AdminView } from './adminNavigation.ts'
import WorkspaceFrame from '../workspace/WorkspaceFrame.tsx'

interface Props {
  children: ReactNode
  navigation: readonly AdminNavItem[]
  currentView: AdminView
  icons: Record<AdminView, LucideIcon>
  onNavigate: (view: AdminView) => void
  identityLabel: string
  onLogout: () => void
}
export default function AdminFrame(props: Props) {
  return (
    <WorkspaceFrame<AdminView>
      {...props}
      panelLabel="Admin Panel"
      navigationLabel="Admin navigation"
      identityRole="Administrator"
      onProfile={
        props.navigation.some((item) => item.key === 'profile') ? () => props.onNavigate('profile') : undefined
      }
      onNotices={
        props.navigation.some((item) => item.key === 'notices') ? () => props.onNavigate('notices') : undefined
      }
    />
  )
}
