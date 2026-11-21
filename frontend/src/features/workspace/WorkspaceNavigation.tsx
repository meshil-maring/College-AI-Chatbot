import { useState, type ReactNode } from 'react'
import { ChevronDown, type LucideIcon } from 'lucide-react'

export interface WorkspaceNavItem<View extends string> {
  key: View
  label: string
  /** Optional section heading; consecutive items with the same group share one heading. */
  group?: string
}

interface Props<View extends string> {
  navigation: readonly WorkspaceNavItem<View>[]
  currentView: View
  icons: Record<View, LucideIcon>
  label: string
  collapsed: boolean
  onSelect: (view: View) => void
  /** Views whose sub-pages can be shown or hidden with a chevron. */
  expandableViews?: readonly View[]
  renderChildren?: (view: View) => ReactNode
}

/** Group consecutive items under their heading, keeping the configured order. */
function sections<View extends string>(items: readonly WorkspaceNavItem<View>[]) {
  const result: { group?: string; items: WorkspaceNavItem<View>[] }[] = []
  for (const item of items) {
    const last = result[result.length - 1]
    if (last && last.group === item.group) last.items.push(item)
    else result.push({ group: item.group, items: [item] })
  }
  return result
}

/**
 * Sidebar navigation: optional section headings, and sub-pages that open for
 * the current view and can be shown or hidden. In the collapsed icon rail only
 * the icons remain, each with its label as a tooltip.
 */
export default function WorkspaceNavigation<View extends string>({
  navigation,
  currentView,
  icons,
  label,
  collapsed,
  onSelect,
  expandableViews = [],
  renderChildren,
}: Props<View>) {
  // Undefined means "follow the current view": a section is open while you are on it.
  const [toggled, setToggled] = useState<Partial<Record<View, boolean>>>({})
  const isOpen = (view: View) => toggled[view] ?? view === currentView

  return (
    <nav aria-label={label} className="workspace-navigation">
      {sections(navigation).map((section, index) => {
        const headingId = section.group ? `workspace-nav-group-${index}` : undefined
        return (
          <div
            key={section.group ?? `section-${index}`}
            className="workspace-nav-section"
            role={section.group ? 'group' : undefined}
            aria-labelledby={headingId}
          >
            {section.group ? (
              <p id={headingId} className="workspace-nav-heading">
                {section.group}
              </p>
            ) : null}
            <ul>
              {section.items.map((item) => {
                const Icon: LucideIcon = icons[item.key]
                const active = item.key === currentView
                const expandable = expandableViews.includes(item.key)
                const open = expandable && isOpen(item.key)
                const childrenId = `workspace-subnav-${item.key}`
                return (
                  <li key={item.key} className={expandable ? 'workspace-nav-parent' : undefined}>
                    <div className="workspace-nav-row">
                      <button
                        type="button"
                        className={`admin-nav-item ${active ? 'active' : ''}`}
                        aria-current={active ? 'page' : undefined}
                        title={collapsed ? item.label : undefined}
                        onClick={() => {
                          onSelect(item.key)
                          if (expandable) setToggled((previous) => ({ ...previous, [item.key]: true }))
                        }}
                      >
                        <Icon aria-hidden="true" />
                        <span className="admin-nav-label">{item.label}</span>
                      </button>
                      {expandable && !collapsed ? (
                        <button
                          type="button"
                          className={`workspace-nav-toggle ${open ? 'is-open' : ''}`}
                          aria-label={`${open ? 'Hide' : 'Show'} ${item.label} pages`}
                          aria-expanded={open}
                          aria-controls={childrenId}
                          onClick={() => setToggled((previous) => ({ ...previous, [item.key]: !open }))}
                        >
                          <ChevronDown aria-hidden="true" />
                        </button>
                      ) : null}
                    </div>
                    {expandable ? (
                      open && !collapsed ? (
                        <div id={childrenId}>{renderChildren?.(item.key)}</div>
                      ) : null
                    ) : collapsed ? null : (
                      renderChildren?.(item.key)
                    )}
                  </li>
                )
              })}
            </ul>
          </div>
        )
      })}
    </nav>
  )
}
