import { ChevronDown, GraduationCap } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { getAcademicArea, type AcademicPage } from './academicOverviewModel.ts'

interface Props {
  /** Null when Academic Setup is not the open view, so nothing appears selected. */
  page: AcademicPage | null
  onNavigate: (page: AcademicPage) => void
}

const groups: { id: string; title: string; pages: readonly AcademicPage[] }[] = [
  {
    id: 'foundation',
    title: 'Foundations',
    pages: ['departments', 'programs', 'calendar', 'subjects'],
  },
  { id: 'curriculum', title: 'Curriculum & options', pages: ['curriculum'] },
  { id: 'delivery', title: 'Classes & enrollment', pages: ['cohorts', 'sections', 'offerings', 'enrollments'] },
]

export default function AcademicSidebar({ page, onNavigate }: Props) {
  const ref = useRef<HTMLElement>(null)
  useEffect(() => {
    const current = ref.current?.querySelector('[aria-current="page"]')
    const group = current?.closest<HTMLDetailsElement>('details.academic-navigation-section')
    if (group) group.open = true
  }, [page])
  function item(destination: AcademicPage, nested = false) {
    const area = getAcademicArea(destination)
    const Icon = area?.icon ?? GraduationCap
    const active =
      page === null
        ? false
        : page === destination ||
          ((page === 'curriculum-options' || page === 'program-semesters') && destination === 'curriculum-subjects')
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
    <nav ref={ref} aria-label="Academic Setup navigation" className="academic-subnav">
      {item('overview')}
      {groups.map((group) => (
        // Only the section holding the current page opens (see the effect above), which
        // keeps the rest of the admin sidebar in view.
        <details key={group.id} className="academic-navigation-section">
          <summary>
            {group.title}
            <ChevronDown aria-hidden="true" />
          </summary>
          {group.pages
            .map((page) => getAcademicArea(page)!)
            .map((area) =>
              area.page === 'calendar' || area.page === 'curriculum' ? (
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
        </details>
      ))}
      {item('quick-setup')}
      {item('guide')}
    </nav>
  )
}
