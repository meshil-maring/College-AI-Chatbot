import {
  BadgeCheck,
  BookOpenCheck,
  ClipboardCheck,
  KeyRound,
  MailPlus,
  ShieldCheck,
  UsersRound,
  type LucideIcon,
} from 'lucide-react'
import type { StaffFacultyPage } from '../adminNavigation.ts'
import '../students/studentWorkspace.css'

/** Sidebar labels, page headings and descriptions for each Staff and Faculty page. */
export const STAFF_FACULTY_PAGE_INFO: Record<
  StaffFacultyPage,
  { label: string; description: string; Icon: LucideIcon }
> = {
  requests: {
    label: 'Requests',
    description: 'Approve Staff and Faculty sign-up requests into a role and department.',
    Icon: ClipboardCheck,
  },
  invitations: {
    label: 'Pending invitations',
    description: 'Invite new Staff or Faculty by email and follow up on invitations that are not accepted yet.',
    Icon: MailPlus,
  },
  roster: {
    label: 'Roster',
    description:
      'Everyone on staff: change roles and departments, appoint Heads of Department and deactivate accounts.',
    Icon: UsersRound,
  },
  responsibilities: {
    label: 'Responsibilities',
    description:
      'Extra duties of Faculty: the Head of Department rule, Class In-Charge of a section and Subject Coordinator of a course.',
    Icon: BadgeCheck,
  },
  teaching: {
    label: 'Teaching',
    description:
      'Who teaches which subject and class. Teaching outside a teacher’s departments needs that department’s Head to approve it.',
    Icon: BookOpenCheck,
  },
  administrators: {
    label: 'Administrators',
    description: 'Everyone who administers the institution. The Owner invites or removes administrators.',
    Icon: ShieldCheck,
  },
  permissions: {
    label: 'Staff permissions',
    description: 'Give active Staff members extra duties beyond their role.',
    Icon: KeyRound,
  },
}

export function staffFacultyPages(canManagePermissions: boolean): StaffFacultyPage[] {
  const pages: StaffFacultyPage[] = [
    'requests',
    'invitations',
    'roster',
    'responsibilities',
    'teaching',
    'administrators',
  ]
  return canManagePermissions ? [...pages, 'permissions'] : pages
}

export default function StaffFacultyNavigation({
  currentPage,
  canManagePermissions,
  onNavigate,
}: {
  /** Null when another admin view is open, so no sub-page appears selected. */
  currentPage: StaffFacultyPage | null
  canManagePermissions: boolean
  onNavigate: (page: StaffFacultyPage) => void
}) {
  return (
    <ul className="student-sidebar-subnav" aria-label="Staff and Faculty pages">
      {staffFacultyPages(canManagePermissions).map((page) => {
        const { label, Icon } = STAFF_FACULTY_PAGE_INFO[page]
        return (
          <li key={page}>
            <button
              type="button"
              className="student-workspace-navigation-item"
              aria-current={currentPage === page ? 'page' : undefined}
              onClick={() => onNavigate(page)}
            >
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
