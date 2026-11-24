import type { ReactNode } from 'react'
import { navigateTo } from '../../../../lib/navigation.ts'
import type { StudentWorkspacePage } from '../../adminNavigation.ts'

/** Build a Students workspace URL that keeps unrelated query state out of the link. */
export function studentPageHref(page: StudentWorkspacePage) {
  const params = new URLSearchParams(window.location.search)
  params.set('view', 'approvals')
  if (page === 'register') params.delete('student-page')
  else params.set('student-page', page)
  params.delete('academic')
  params.delete('academic-search')
  params.delete('student-search')
  return `${window.location.pathname}?${params.toString()}`
}

/** In-app link to another Students page; keeps a real href for new-tab and copy-link use. */
export default function StudentPageLink({
  page,
  className,
  children,
}: {
  page: StudentWorkspacePage
  className?: string
  children: ReactNode
}) {
  const href = studentPageHref(page)
  return (
    <a
      href={href}
      className={className}
      onClick={(event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return
        event.preventDefault()
        navigateTo(href)
      }}
    >
      {children}
    </a>
  )
}
