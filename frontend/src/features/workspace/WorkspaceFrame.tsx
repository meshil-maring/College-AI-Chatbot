import { useEffect, useState, type ReactNode } from 'react'
import { Bell, ChevronDown, GraduationCap, LogOut, Menu, X, type LucideIcon } from 'lucide-react'
import WorkspaceNavigation, { type WorkspaceNavItem } from './WorkspaceNavigation.tsx'
import './workspace.css'

const COLLAPSED_KEY = 'collegeai.sidebar.collapsed'

// The collapsed icon rail is a per-browser preference; storage may be unavailable.
function readCollapsed(): boolean {
  try {
    return window.localStorage.getItem(COLLAPSED_KEY) === '1'
  } catch {
    return false
  }
}
function writeCollapsed(value: boolean) {
  try {
    window.localStorage.setItem(COLLAPSED_KEY, value ? '1' : '0')
  } catch {
    // Ignore: the rail still works for this page view.
  }
}

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
  expandableViews,
  sidebarContent,
  collapsible = true,
}: {
  children: ReactNode
  navigation: readonly WorkspaceNavItem<View>[]
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
  /** Views whose sub-pages open for the current view and can be shown or hidden. */
  expandableViews?: readonly View[]
  sidebarContent?: ReactNode
  collapsible?: boolean
}) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => collapsible && readCollapsed())
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
  // The rail exists only on larger screens; mobile always uses the full overlay.
  const rail = collapsed && !mobileViewport
  const initials =
    identityLabel
      .replace(/@.*$/, '')
      .split(/[\s._-]+/)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase() || identityRole[0]
  const close = () => setMobileOpen(false)
  const toggleNavigation = () => {
    if (mobileViewport || !collapsible) {
      setMobileOpen(!mobileOpen)
      return
    }
    writeCollapsed(!collapsed)
    setCollapsed(!collapsed)
  }
  return (
    <div
      className={`admin-workspace ${workspaceClassName} ${rail ? 'sidebar-collapsed' : ''}`}
      onKeyDown={(event) => {
        if (event.key === 'Escape') setMobileOpen(false)
      }}
    >
      {mobileOpen && (
        <button type="button" className="admin-sidebar-scrim" aria-label="Close navigation overlay" onClick={close} />
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
          <button type="button" className="admin-mobile-toggle" aria-label="Close navigation" onClick={close}>
            <X aria-hidden="true" />
          </button>
        </div>
        <div className="workspace-sidebar-scroll">
          <p className="admin-sidebar-caption">{panelLabel}</p>
          {navigation.length > 0 && (
            <WorkspaceNavigation<View>
              navigation={navigation}
              currentView={currentView}
              icons={icons}
              label={navigationLabel}
              collapsed={rail}
              expandableViews={expandableViews}
              onSelect={(view) => {
                onNavigate(view)
                close()
              }}
              renderChildren={renderNavigationChildren ? (view) => renderNavigationChildren(view, close) : undefined}
            />
          )}
          {rail ? null : sidebarContent}
        </div>
        <div className="admin-sidebar-bottom">
          <span className="admin-avatar workspace-account-avatar" aria-hidden="true">
            {initials}
          </span>
          <span className="workspace-account-identity">
            <strong>{identityLabel}</strong>
            <small>{identityRole}</small>
          </span>
          <button type="button" aria-label="Sign out" title="Sign out" onClick={onLogout}>
            <LogOut aria-hidden="true" />
            <span className="workspace-signout-label">Sign out</span>
          </button>
        </div>
      </aside>
      <div className="admin-workspace-body">
        <header className="admin-topbar">
          <button
            type="button"
            className={`admin-mobile-toggle ${collapsible ? 'workspace-navigation-toggle' : ''}`}
            aria-label={collapsible ? 'Toggle navigation' : 'Open navigation'}
            aria-expanded={collapsible && !mobileViewport ? !collapsed : mobileOpen}
            aria-controls="workspace-sidebar"
            title={collapsible && !mobileViewport ? (collapsed ? 'Expand sidebar' : 'Collapse sidebar') : undefined}
            onClick={toggleNavigation}
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
