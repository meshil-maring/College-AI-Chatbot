import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import {
  ADMIN_EXPANDABLE_VIEWS,
  type AdminNavItem,
  type AdminView,
  type StaffFacultyPage,
  type StudentWorkspacePage,
} from './adminNavigation.ts'
import WorkspaceFrame from '../workspace/WorkspaceFrame.tsx'
import AcademicSidebar from './academic-setup/overview/AcademicSidebar.tsx'
import AcademicSearch from './academic-setup/overview/AcademicSearch.tsx'
import type { AcademicPage } from './academic-setup/overview/academicOverviewModel.ts'
import StudentWorkspaceNavigation from './students/StudentWorkspaceNavigation.tsx'
import StaffFacultyNavigation from './staff-faculty/StaffFacultyNavigation.tsx'

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
  studentPage: StudentWorkspacePage
  onStudentNavigate: (page: StudentWorkspacePage) => void
  staffPage: StaffFacultyPage
  onStaffNavigate: (page: StaffFacultyPage) => void
  canManagePermissions: boolean
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
      expandableViews={ADMIN_EXPANDABLE_VIEWS}
      workspaceClassName={academic ? 'academic-admin-workspace' : undefined}
      headerContent={
        academic ? <AcademicSearch value={props.academicSearch} onChange={props.onAcademicSearch} /> : undefined
      }
      renderNavigationChildren={(view, close) => {
        if (view === 'approvals')
          return (
            <StudentWorkspaceNavigation
              // A sub-page is only "current" while the Students view is open.
              currentPage={props.currentView === 'approvals' ? props.studentPage : null}
              onNavigate={(page) => {
                props.onStudentNavigate(page)
                close()
              }}
            />
          )
        if (view === 'staff-faculty')
          return (
            <StaffFacultyNavigation
              currentPage={props.currentView === 'staff-faculty' ? props.staffPage : null}
              canManagePermissions={props.canManagePermissions}
              onNavigate={(page) => {
                props.onStaffNavigate(page)
                close()
              }}
            />
          )
        return view === 'academic-setup' ? (
          <AcademicSidebar
            page={academic ? props.academicPage : null}
            onNavigate={(page) => {
              props.onAcademicNavigate(page)
              close()
            }}
          />
        ) : null
      }}
      onProfile={
        props.navigation.some((item) => item.key === 'profile') ? () => props.onNavigate('profile') : undefined
      }
      onNotices={
        props.navigation.some((item) => item.key === 'notices') ? () => props.onNavigate('notices') : undefined
      }
    />
  )
}
