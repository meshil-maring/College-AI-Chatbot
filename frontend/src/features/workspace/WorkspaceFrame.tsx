import { useEffect, useState, type ReactNode } from 'react'
import { Bell, ChevronDown, GraduationCap, LogOut, Menu, X, type LucideIcon } from 'lucide-react'
import './workspace.css'

export default function WorkspaceFrame<View extends string>({
  children,
  navigation,
  currentView,
  icons,
  onNavigate,
  panelLabel,
  navigationLabel,
  identityLabel,
  identityRole,
  onLogout,
  onProfile,
  onNotices,
  brand,
  headerContent,
  workspaceClassName = '',
  renderNavigationChildren,
  sidebarContent,
  collapsible = true,
}: {
  children: ReactNode
  navigation: readonly { key: View; label: string }[]
  currentView: View
  icons: Record<View, LucideIcon>
  onNavigate: (view: View) => void
  panelLabel: string
  navigationLabel: string
  identityLabel: string
  identityRole: string
  onLogout: () => void
  onProfile?: () => void
  onNotices?: () => void
  brand?: ReactNode
  headerContent?: ReactNode
  workspaceClassName?: string
  renderNavigationChildren?: (view: View, close: () => void) => ReactNode
  sidebarContent?: ReactNode
  collapsible?: boolean
}) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [mobileViewport, setMobileViewport] = useState(() => window.matchMedia?.('(max-width: 760px)').matches ?? false)
  useEffect(() => {
    const media = window.matchMedia?.('(max-width: 760px)')
    const update = () => {
      setMobileViewport(Boolean(media?.matches))
      setMobileOpen(false)
    }
    media?.addEventListener('change', update)
    return () => media?.removeEventListener('change', update)
  }, [])
  const initials =
    identityLabel
      .replace(/@.*$/, '')
      .split(/[\s._-]+/)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase() || identityRole[0]
  const go = (view: View) => {
    onNavigate(view)
    setMobileOpen(false)
  }
  return (
    <div
      className={`admin-workspace ${workspaceClassName} ${mobileOpen ? 'navigation-toggled' : ''}`}
      onKeyDown={(event) => {
        if (event.key === 'Escape') setMobileOpen(false)
      }}
    >
      {mobileOpen && (
        <button
          type="button"
          className="admin-sidebar-scrim"
          aria-label="Close navigation overlay"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside id="workspace-sidebar" className={`admin-sidebar ${mobileOpen ? 'is-open' : ''}`}>
        <div className="admin-brand">
          {brand ?? (
            <span className="workspace-brand">
              <GraduationCap aria-hidden="true" />
              <span>
                College<span>AI</span>
              </span>
            </span>
          )}
          <button
            type="button"
            className="admin-mobile-toggle"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          >
            <X aria-hidden="true" />
          </button>
        </div>
        <p className="admin-sidebar-caption">{panelLabel}</p>
        {navigation.length > 0 && (
          <nav aria-label={navigationLabel}>
            <ul>
              {navigation.map((item) => {
                const Icon: LucideIcon = icons[item.key]
                const active = item.key === currentView
                return (
                  <li key={item.key}>
                    <button
                      type="button"
                      className={`admin-nav-item ${active ? 'active' : ''}`}
                      aria-current={active ? 'page' : undefined}
                      onClick={() => go(item.key)}
                    >
                      <Icon aria-hidden="true" />
                      <span>{item.label}</span>
                    </button>
                    {renderNavigationChildren?.(item.key, () => setMobileOpen(false))}
                  </li>
                )
              })}
            </ul>
          </nav>
        )}
        {sidebarContent}
        <div className="admin-sidebar-bottom">
          <span className="admin-institution-mark" />
          <span>Institution workspace</span>
          <button type="button" aria-label="Sign out" title="Sign out" onClick={onLogout}>
            <LogOut aria-hidden="true" />
          </button>
        </div>
      </aside>
      <div className="admin-workspace-body">
        <header className="admin-topbar">
          <button
            type="button"
            className={`admin-mobile-toggle ${collapsible ? 'workspace-navigation-toggle' : ''}`}
            aria-label={collapsible ? 'Toggle navigation' : 'Open navigation'}
            aria-expanded={collapsible && !mobileViewport ? !mobileOpen : mobileOpen}
            aria-controls="workspace-sidebar"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            <Menu aria-hidden="true" />
          </button>
          {headerContent ?? <span className="admin-topbar-label">{identityRole} workspace</span>}
          <div className="admin-topbar-account">
            {onNotices && (
              <button
                type="button"
                className="admin-notice-button"
                aria-label="View notices"
                title="Notices"
                onClick={onNotices}
              >
                <Bell aria-hidden="true" />
              </button>
            )}
            <button
              type="button"
              className="admin-profile-button"
              aria-label={`Open ${identityRole.toLowerCase()} profile`}
              disabled={!onProfile}
              onClick={onProfile}
            >
              <span className="admin-avatar">{initials}</span>
              <span className="admin-profile-label">
                <strong>{identityLabel}</strong>
                <small>{identityRole}</small>
              </span>
              <ChevronDown aria-hidden="true" />
            </button>
          </div>
        </header>
        <p className="sr-only">Signed in as {identityLabel}</p>
        <main className="admin-main">{children}</main>
      </div>
    </div>
  )
}
