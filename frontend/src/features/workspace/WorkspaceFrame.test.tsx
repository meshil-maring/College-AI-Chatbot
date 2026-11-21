import { fireEvent, render, screen, within } from '@testing-library/react'
import { BookOpen, Users, UserCircle } from 'lucide-react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import WorkspaceFrame from './WorkspaceFrame.tsx'

type View = 'setup' | 'people' | 'profile'
const navigation = [
  { key: 'setup' as const, label: 'Setup', group: 'Academics' },
  { key: 'people' as const, label: 'People', group: 'Team' },
  { key: 'profile' as const, label: 'Profile', group: 'Account' },
]
const icons = { setup: BookOpen, people: Users, profile: UserCircle }

function renderFrame(currentView: View = 'setup', onNavigate = vi.fn()) {
  return render(
    <WorkspaceFrame<View>
      navigation={navigation}
      currentView={currentView}
      icons={icons}
      onNavigate={onNavigate}
      panelLabel="Admin Panel"
      navigationLabel="Test navigation"
      identityLabel="admin@example.test"
      identityRole="Administrator"
      onLogout={vi.fn()}
      expandableViews={['setup', 'people']}
      renderNavigationChildren={(view) => <p>{view} pages</p>}
    >
      <p>Content</p>
    </WorkspaceFrame>,
  )
}

afterEach(() => window.localStorage.clear())

describe('WorkspaceFrame sidebar', () => {
  it('shows section headings as labelled groups', () => {
    renderFrame()
    const nav = screen.getByRole('navigation', { name: 'Test navigation' })
    expect(within(nav).getByRole('group', { name: 'Academics' })).toHaveTextContent('Setup')
    expect(within(nav).getByRole('group', { name: 'Account' })).toHaveTextContent('Profile')
  })

  it('opens only the current view sub-pages and lets them be shown or hidden', () => {
    renderFrame('setup')
    expect(screen.getByText('setup pages')).toBeInTheDocument()
    expect(screen.queryByText('people pages')).toBeNull()

    const hideSetup = screen.getByRole('button', { name: 'Hide Setup pages' })
    expect(hideSetup).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(hideSetup)
    expect(screen.queryByText('setup pages')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Show People pages' }))
    expect(screen.getByText('people pages')).toBeInTheDocument()
  })

  it('marks only the current view as the current page', () => {
    renderFrame('people')
    expect(screen.getByRole('button', { name: 'People' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('button', { name: 'Setup' })).not.toHaveAttribute('aria-current')
  })

  it('collapses to a remembered icon rail with tooltips instead of hiding navigation', () => {
    const { container, unmount } = renderFrame()
    const toggle = screen.getByRole('button', { name: 'Toggle navigation' })
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(container.querySelector('.admin-workspace')).toHaveClass('sidebar-collapsed')
    // Destinations stay reachable as icons, labelled for tooltips and assistive tech.
    expect(screen.getByRole('button', { name: 'Setup' })).toHaveAttribute('title', 'Setup')
    expect(screen.queryByText('setup pages')).toBeNull()
    expect(screen.queryByRole('button', { name: /Setup pages/ })).toBeNull()
    unmount()

    renderFrame()
    expect(screen.getByRole('button', { name: 'Toggle navigation' })).toHaveAttribute('aria-expanded', 'false')
  })

  it('shows who is signed in with a labelled sign-out action', () => {
    renderFrame()
    const footer = screen.getByRole('button', { name: 'Sign out' }).closest('.admin-sidebar-bottom') as HTMLElement
    expect(within(footer).getByText('admin@example.test')).toBeInTheDocument()
    expect(within(footer).getByText('Sign out')).toBeInTheDocument()
  })
})
