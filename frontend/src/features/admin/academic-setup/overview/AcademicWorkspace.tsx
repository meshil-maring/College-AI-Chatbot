import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../../../auth/session/AuthProvider.tsx'
import type { AcademicEntity } from '../../../../types/academicSetup.ts'
import AcademicOverviewSession from './AcademicOverviewSession.tsx'
import { academicPageView } from './academicPageViews.tsx'
import { type AcademicPage } from './academicOverviewModel.ts'
import { hasAcademicCatalogueReadAccess } from './useAcademicOverview.ts'
import '../styles/overview.css'
import AcademicJourney from '../navigation/AcademicJourney.tsx'

interface Props {
  page: AcademicPage
  search: string
  onNavigate: (page: AcademicPage) => void
  onClearSearch: () => void
}

export default function AcademicWorkspace(props: Props) {
  const { accessToken, sessionGeneration, user, role } = useAuth()
  if (!accessToken || !user || role !== 'admin' || !user.institution_id)
    return <p role="status">Administrator access is unavailable.</p>
  const identity = JSON.stringify([
    sessionGeneration ?? accessToken,
    user.user_id,
    user.institution_id,
    user.effective_permissions,
  ])
  return (
    <AcademicWorkspaceSession
      key={identity}
      {...props}
      accessToken={accessToken}
      identity={identity}
      institutionId={user.institution_id}
      canReadCatalogues={hasAcademicCatalogueReadAccess(user.effective_permissions)}
    />
  )
}

function AcademicWorkspaceSession(
  props: Props & { accessToken: string; identity: string; institutionId: string; canReadCatalogues: boolean },
) {
  const ref = useRef<HTMLDivElement>(null)
  const focusTab = useRef(false)
  function navigate(page: AcademicPage) {
    focusTab.current = page !== props.page && document.activeElement?.getAttribute('role') === 'tab'
    props.onNavigate(page)
  }
  useEffect(() => {
    const heading = focusTab.current
      ? ref.current?.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]')
      : ref.current?.querySelector('h1')
    focusTab.current = false
    if (!heading || document.querySelector('dialog[open]')) return
    if (!document.activeElement?.matches('input[type="search"]')) {
      if (heading.tagName === 'H1') heading.tabIndex = -1
      heading.focus({ preventScroll: true })
    }
    ref.current?.scrollIntoView?.({ block: 'start' })
  }, [props.page])
  return (
    <div ref={ref} className="academic-workspace-flow">
      <AcademicJourney page={props.page} onNavigate={navigate} />
      <AcademicWorkspaceContent {...props} onNavigate={navigate} />
    </div>
  )
}

function AcademicWorkspaceContent(
  props: Props & { accessToken: string; identity: string; institutionId: string; canReadCatalogues: boolean },
) {
  const [request, setRequest] = useState<{ entity?: AcademicEntity; create: boolean }>({ create: false })
  /** Overview shortcuts open the page that owns an entity, optionally straight into its "add" drawer. */
  function openRecords(entity?: AcademicEntity, create = false) {
    setRequest({ entity, create })
    props.onNavigate(entity ? ENTITY_PAGES[entity] : 'overview')
  }
  const View = academicPageView(props.page)
  if (View)
    return (
      <View
        page={props.page}
        context={{
          accessToken: props.accessToken,
          identity: props.identity,
          institutionId: props.institutionId,
          canReadCatalogues: props.canReadCatalogues,
        }}
        navigate={props.onNavigate}
        createRequest={request}
        clearRequest={() => setRequest({ create: false })}
      />
    )
  return <AcademicOverviewSession {...props} onOpenRecords={openRecords} />
}

const ENTITY_PAGES: Record<AcademicEntity, AcademicPage> = {
  departments: 'departments',
  programs: 'programs',
  courses: 'subjects',
  academic_years: 'years',
  semesters: 'terms',
}
