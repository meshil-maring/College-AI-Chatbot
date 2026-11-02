import { ClipboardCheck, FileSpreadsheet, UserPlus, UsersRound } from 'lucide-react'
import type { StudentWorkspacePage } from '../adminNavigation.ts'

const pages: { id: StudentWorkspacePage; label: string; Icon: typeof UserPlus }[] = [
  { id: 'all', label: 'All Students', Icon: UsersRound },
  { id: 'register', label: 'Add Student', Icon: UserPlus },
  { id: 'bulk', label: 'Bulk Import', Icon: FileSpreadsheet },
  { id: 'requests', label: 'Registration Requests', Icon: ClipboardCheck },
]

export default function StudentWorkspaceNavigation({
  currentPage,
  onNavigate,
}: {
  currentPage: StudentWorkspacePage
  onNavigate: (page: StudentWorkspacePage) => void
}) {
  return (
    <ul className="student-sidebar-subnav" aria-label="Students pages">
      {pages.map(({ id, label, Icon }) => (
        <li key={id}>
          <button
            type="button"
            className="student-workspace-navigation-item"
            aria-current={currentPage === id ? 'page' : undefined}
            onClick={() => onNavigate(id)}
          >
            <Icon size={18} aria-hidden="true" />
            <span>{label}</span>
          </button>
        </li>
      ))}
    </ul>
  )
}
