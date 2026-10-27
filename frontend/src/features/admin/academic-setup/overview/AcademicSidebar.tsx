import { ChevronDown, GraduationCap } from 'lucide-react'
import { getAcademicArea, type AcademicPage } from './academicOverviewModel.ts'

interface Props {
  page: AcademicPage
  onNavigate: (page: AcademicPage) => void
}

const sidebarPages: readonly AcademicPage[] = [
  'departments',
  'programs',
  'calendar',
  'program-semesters',
  'subjects',
  'curriculum',
  'cohorts',
  'sections',
  'offerings',
]

export default function AcademicSidebar({ page, onNavigate }: Props) {
  function item(destination: AcademicPage, nested = false) {
    const area = getAcademicArea(destination)
    const Icon = area?.icon ?? GraduationCap
    const active = page === destination
    return (
      <button
        key={destination}
        type="button"
        className={`academic-nav-link ${nested ? 'is-nested' : ''} ${active ? 'is-current' : ''}`}
        aria-current={active ? 'page' : undefined}
        onClick={() => onNavigate(destination)}
      >
        <Icon aria-hidden="true" />
        <span>{area?.title ?? 'Overview'}</span>
      </button>
    )
  }

  return (
    <nav aria-label="Academic Setup navigation" className="academic-subnav">
      {item('overview')}
      {sidebarPages
        .map((page) => getAcademicArea(page)!)
        .map((area) =>
          area.page === 'calendar' ? (
            <div key={area.page} className="academic-nav-group">
              {item(area.page)}
              {area.children?.map((child) => item(child, true))}
            </div>
          ) : area.children ? (
            <details key={area.page} open className="academic-nav-group">
              <summary>
                <area.icon aria-hidden="true" />
                <span>{area.title}</span>
                <ChevronDown aria-hidden="true" className="academic-nav-chevron" />
              </summary>
              {area.children.map((child) => item(child, true))}
            </details>
          ) : (
            item(area.page)
          ),
        )}
    </nav>
  )
}
