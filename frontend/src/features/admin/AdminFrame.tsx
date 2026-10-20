import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import type { AdminNavItem, AdminView } from './adminNavigation.ts'
import { STUDENT_SECTIONS, type StudentSection } from './students/studentSections.ts'
import { StudentsNavigation } from '../students/StudentsUI.tsx'
import WorkspaceFrame from '../workspace/WorkspaceFrame.tsx'
import { studentsPageHref } from '../students/studentsNavigation.ts'

interface Props {
  children: ReactNode
  navigation: readonly AdminNavItem[]
  currentView: AdminView
  icons: Record<AdminView, LucideIcon>
  onNavigate: (view: AdminView) => void
  studentSection: StudentSection
  onStudentSection: (section: StudentSection) => void
  identityLabel: string
  onLogout: () => void
  onSearch: (search: string) => void
  canReviewStudents: boolean
  canReadStudentHistory: boolean
  canRegisterStudents: boolean
  studentSectionId?: string
}

export default function AdminFrame(props: Props) {
  return <WorkspaceFrame<AdminView> navigation={props.navigation} currentView={props.currentView} icons={props.icons} onNavigate={props.onNavigate}
    studentsView="students" studentsNavigationId="admin-students-pages"
    studentsNavigation={<StudentsNavigation id="admin-students-pages" active={props.studentSection} items={STUDENT_SECTIONS.map((item) => ({ ...item, href: studentsPageHref('admin', item.key, 'individual', props.studentSectionId),
      disabled: item.key === 'history' ? !props.canReadStudentHistory : item.key === 'waiting-approval' ? !props.canReviewStudents : item.key === 'register' ? !props.canRegisterStudents : false,
      title: item.key === 'history' && !props.canReadStudentHistory ? 'Student history access is required' : item.key === 'waiting-approval' && !props.canReviewStudents ? 'Student approval access is required' : item.key === 'register' && !props.canRegisterStudents ? 'Student registration access is required' : undefined,
    }))} onNavigate={props.onStudentSection} />}
    panelLabel="Admin Panel" navigationLabel="Admin navigation" identityLabel={props.identityLabel} identityRole="Administrator" onLogout={props.onLogout}
    onSearch={props.navigation.some((item) => item.key === 'students') ? props.onSearch : undefined}
    onProfile={props.navigation.some((item) => item.key === 'profile') ? () => props.onNavigate('profile') : undefined}
    onNotices={props.navigation.some((item) => item.key === 'notices') ? () => props.onNavigate('notices') : undefined}>
    {props.children}
  </WorkspaceFrame>
}
