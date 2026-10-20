import { navigateTo } from '../../lib/navigation.ts'
import { facultyStudentsPath } from './facultyRoutes.ts'
import { useFacultyStudentSections } from './useFacultyStudentSections.ts'
import './facultyStudentsNavigation.css'

const pages = [
  { page: 'roster', label: 'Roster' },
  { page: 'history', label: 'Record history' },
  { page: 'waiting-approval', label: 'Waiting approval' },
  { page: 'register', label: 'Register' },
] as const

export default function FacultyStudentsNavigation({ accessToken, scopeVersion, onNavigate }: {
  accessToken: string
  scopeVersion?: string
  onNavigate?: () => void
}) {
  const { page, sectionId, selected } = useFacultyStudentSections(accessToken, scopeVersion)
  return <nav id="faculty-students-pages" aria-label="Students pages" className="faculty-students-links">
    {pages.map(({ page: target, label }) => {
      const active = target === page
      if (target === 'register' && !selected?.can_manage) return <span key={target} aria-disabled="true" aria-current={active ? 'page' : undefined} title="Registration requires permission to manage this section">{label}</span>
      const href = facultyStudentsPath(selected?.section_id ?? (sectionId || undefined), target)
      return <a key={target} href={href} aria-current={active ? 'page' : undefined} className={active ? 'active' : ''} onClick={(event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
        event.preventDefault()
        navigateTo(href)
        onNavigate?.()
      }}>{label}</a>
    })}
  </nav>
}
