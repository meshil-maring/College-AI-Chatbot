import { useState, type ReactNode } from 'react'
import {
  Bell,
  ChevronDown,
  LogOut,
  Menu,
  Search,
  X,
  type LucideIcon,
} from 'lucide-react'
import type { AdminNavItem, AdminView } from './adminNavigation.ts'
import {
  STUDENT_SECTIONS,
  type StudentSection,
} from './students/studentSections.ts'
import './adminWorkspace.css'

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
}

export default function AdminFrame({
  children,
  navigation,
  currentView,
  icons,
  onNavigate,
  studentSection,
  onStudentSection,
  identityLabel,
  onLogout,
  onSearch,
}: Props) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [search, setSearch] = useState('')
  const initials =
    identityLabel
      .replace(/@.*$/, '')
      .split(/[\s._-]+/)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase() || 'A'
  const go = (view: AdminView) => {
    onNavigate(view)
    setMobileOpen(false)
  }
  const canSearch = navigation.some((item) => item.key === 'students')

  return (
    <div className="admin-workspace">
      {mobileOpen && (
        <button
          className="admin-sidebar-scrim"
          aria-label="Close navigation overlay"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        id="admin-sidebar"
        className={`admin-sidebar ${mobileOpen ? 'is-open' : ''}`}
      >
        <div className="admin-brand">
          <span>
            College<span>AI</span>
          </span>
          <button
            className="admin-mobile-toggle"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          >
            <X />
          </button>
        </div>
        <p className="admin-sidebar-caption">Admin Panel</p>
        {navigation.length > 0 && (
          <nav aria-label="Admin navigation">
            <ul>
              {navigation.map((item) => {
                const Icon = icons[item.key]
                const active = item.key === currentView
                return (
                  <li key={item.key}>
                    <button
                      className={`admin-nav-item ${active ? 'active' : ''}`}
                      aria-current={active ? 'page' : undefined}
                      onClick={() => go(item.key)}
                    >
                      <Icon />
                      <span>{item.label}</span>
                      {item.key === 'students' && (
                        <ChevronDown
                          className={`admin-nav-chevron ${active ? 'expanded' : ''}`}
                        />
                      )}
                    </button>
                    {item.key === 'students' && active && (
                      <div className="admin-student-links">
                        {STUDENT_SECTIONS.map((section) => (
                          <a
                            key={section.key}
                            href={`#admin/students/${section.key}`}
                            className={
                              studentSection === section.key ? 'active' : ''
                            }
                            aria-current={
                              studentSection === section.key
                                ? 'page'
                                : undefined
                            }
                            onClick={(event) => {
                              event.preventDefault()
                              onStudentSection(section.key)
                              setMobileOpen(false)
                            }}
                          >
                            {section.label}
                          </a>
                        ))}
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
          </nav>
        )}
        <div className="admin-sidebar-bottom">
          <span className="admin-institution-mark" />
          <span>Institution workspace</span>
          <button aria-label="Sign out" title="Sign out" onClick={onLogout}>
            <LogOut />
          </button>
        </div>
      </aside>
      <div className="admin-workspace-body">
        <header className="admin-topbar">
          <button
            className="admin-mobile-toggle"
            aria-label="Open navigation"
            aria-expanded={mobileOpen}
            aria-controls="admin-sidebar"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            <Menu />
          </button>
          {canSearch ? (
            <form
              className="admin-global-search"
              role="search"
              onSubmit={(event) => {
                event.preventDefault()
                onSearch(search)
                go('students')
              }}
            >
              <Search />
              <input
                aria-label="Search student directory"
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search students by student number…"
              />
              <kbd>↵</kbd>
            </form>
          ) : (
            <span className="admin-topbar-label">Institution workspace</span>
          )}
          <div className="admin-topbar-account">
            {navigation.some((item) => item.key === 'notices') && (
              <button
                className="admin-notice-button"
                aria-label="View notices"
                title="Notices"
                onClick={() => go('notices')}
              >
                <Bell />
              </button>
            )}
            <button
              className="admin-profile-button"
              aria-label="Open administrator profile"
              disabled={!navigation.some((item) => item.key === 'profile')}
              onClick={() => go('profile')}
            >
              <span className="admin-avatar">{initials}</span>
              <span className="admin-profile-label">
                <strong>{identityLabel}</strong>
                <small>Administrator</small>
              </span>
              <ChevronDown />
            </button>
          </div>
        </header>
        <p className="sr-only">Signed in as {identityLabel}</p>
        <main
          className={`admin-main ${currentView === 'students' ? 'admin-students-main' : ''}`}
        >
          {children}
        </main>
      </div>
    </div>
  )
}
