import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import type { AdminNavItem, AdminView } from './adminNavigation.ts'
import WorkspaceFrame from '../workspace/WorkspaceFrame.tsx'
import AcademicSidebar from './academic-setup/overview/AcademicSidebar.tsx'
import AcademicSearch from './academic-setup/overview/AcademicSearch.tsx'
import type { AcademicPage } from './academic-setup/overview/academicOverviewModel.ts'

interface Props {
  children: ReactNode
  navigation: readonly AdminNavItem[]
  currentView: AdminView
  icons: Record<AdminView, LucideIcon>
  onNavigate: (view: AdminView) => void
  identityLabel: string
  onLogout: () => void
  academicPage: AcademicPage
  onAcademicNavigate: (page: AcademicPage) => void
  academicSearch: string
  onAcademicSearch: (value: string) => void
}
export default function AdminFrame(props: Props) {
  const academic = props.currentView === 'academic-setup'
  return (
    <WorkspaceFrame<AdminView>
      {...props}
      panelLabel="Admin Panel"
      navigationLabel="Admin navigation"
      identityRole="Administrator"
      collapsible
      workspaceClassName={academic ? 'academic-admin-workspace' : undefined}
      headerContent={
        academic ? <AcademicSearch value={props.academicSearch} onChange={props.onAcademicSearch} /> : undefined
      }
      renderNavigationChildren={
        academic
          ? (view, close) =>
              view === 'academic-setup' && (
                <AcademicSidebar
                  page={props.academicPage}
                  onNavigate={(page) => {
                    props.onAcademicNavigate(page)
                    close()
                  }}
                />
              )
          : undefined
      }
      onProfile={
        props.navigation.some((item) => item.key === 'profile') ? () => props.onNavigate('profile') : undefined
      }
      onNotices={
        props.navigation.some((item) => item.key === 'notices') ? () => props.onNavigate('notices') : undefined
      }
    />
  )
}
