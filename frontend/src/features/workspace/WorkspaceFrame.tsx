import { useState, type ReactNode } from 'react'
import { Bell, ChevronDown, LogOut, Menu, Search, X, type LucideIcon } from 'lucide-react'
import '../admin/adminWorkspace.css'

export default function WorkspaceFrame<View extends string>({ children, navigation, currentView, icons, onNavigate, studentsView, studentsNavigation, studentsNavigationId, panelLabel, navigationLabel, identityLabel, identityRole, onLogout, onSearch, onProfile, onNotices }: {
  children: ReactNode
  navigation: readonly { key: View; label: string }[]
  currentView: View
  icons: Record<View, LucideIcon>
  onNavigate: (view: View) => void
  studentsView: View
  studentsNavigation: ReactNode
  studentsNavigationId: string
  panelLabel: string
  navigationLabel: string
  identityLabel: string
  identityRole: string
  onLogout: () => void
  onSearch?: (search: string) => void
  onProfile?: () => void
  onNotices?: () => void
}) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [expanded, setExpanded] = useState(true)
  const [search, setSearch] = useState('')
  const initials = identityLabel.replace(/@.*$/, '').split(/[\s._-]+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || identityRole[0]
  const studentsActive = currentView === studentsView
  const go = (view: View) => { onNavigate(view); setMobileOpen(false) }

  return <div className="admin-workspace">
    {mobileOpen && <button type="button" className="admin-sidebar-scrim" aria-label="Close navigation overlay" onClick={() => setMobileOpen(false)} />}
    <aside id="workspace-sidebar" className={`admin-sidebar ${mobileOpen ? 'is-open' : ''}`}>
      <div className="admin-brand"><span>College<span>AI</span></span><button type="button" className="admin-mobile-toggle" aria-label="Close navigation" onClick={() => setMobileOpen(false)}><X aria-hidden="true" /></button></div>
      <p className="admin-sidebar-caption">{panelLabel}</p>
      {navigation.length > 0 && <nav aria-label={navigationLabel}>
        <ul>{navigation.map((item) => {
          const Icon: LucideIcon = icons[item.key]
          const active = currentView === item.key
          const students = item.key === studentsView
          return <li key={item.key}>
            <button type="button" className={`admin-nav-item ${active && !students ? 'active' : ''}`} aria-current={active ? 'page' : undefined} aria-expanded={students ? active && expanded : undefined} aria-controls={students && active && expanded ? studentsNavigationId : undefined} onClick={() => {
              if (students) {
                if (active) setExpanded((current) => !current)
                else { setExpanded(true); onNavigate(item.key) }
              } else go(item.key)
            }}><Icon aria-hidden="true" /><span>{item.label}</span>{students && <ChevronDown aria-hidden="true" className={`admin-nav-chevron ${active && expanded ? 'expanded' : ''}`} />}</button>
            {students && active && expanded && <div onClick={(event) => {
              if (event.defaultPrevented && (event.target as HTMLElement).closest('a')) setMobileOpen(false)
            }}>{studentsNavigation}</div>}
          </li>
        })}</ul>
      </nav>}
      <div className="admin-sidebar-bottom"><span className="admin-institution-mark" /><span>Institution workspace</span><button type="button" aria-label="Sign out" title="Sign out" onClick={onLogout}><LogOut aria-hidden="true" /></button></div>
    </aside>
    <div className="admin-workspace-body">
      <header className="admin-topbar">
        <button type="button" className="admin-mobile-toggle" aria-label="Open navigation" aria-expanded={mobileOpen} aria-controls="workspace-sidebar" onClick={() => setMobileOpen(!mobileOpen)}><Menu aria-hidden="true" /></button>
        {onSearch ? <form className="admin-global-search" role="search" onSubmit={(event) => { event.preventDefault(); onSearch(search); setExpanded(true); go(studentsView) }}><Search aria-hidden="true" /><input aria-label="Search student directory" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search students by student number…" /><kbd>↵</kbd></form> : <span className="admin-topbar-label">Institution workspace</span>}
        <div className="admin-topbar-account">
          {onNotices && <button type="button" className="admin-notice-button" aria-label="View notices" title="Notices" onClick={onNotices}><Bell aria-hidden="true" /></button>}
          <button type="button" className="admin-profile-button" aria-label={`Open ${identityRole.toLowerCase()} profile`} disabled={!onProfile} onClick={onProfile}><span className="admin-avatar">{initials}</span><span className="admin-profile-label"><strong>{identityLabel}</strong><small>{identityRole}</small></span><ChevronDown aria-hidden="true" /></button>
        </div>
      </header>
      <p className="sr-only">Signed in as {identityLabel}</p>
      <main className={`admin-main ${studentsActive ? 'admin-students-main' : ''}`}>{children}</main>
    </div>
  </div>
}
