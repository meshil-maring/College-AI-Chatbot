import { useEffect, useRef, useState } from 'react'
import { Info } from 'lucide-react'
import { useAuth } from '../../../auth/session/AuthProvider.tsx'
import type { AcademicEntity } from '../../../../types/academicSetup.ts'
import AcademicSetup from '../AcademicSetup.tsx'
import AcademicOverviewSession from './AcademicOverviewSession.tsx'
import DepartmentsPage from '../departments/DepartmentsPage.tsx'
import ProgramsPage from '../programs/ProgramsPage.tsx'
import SubjectsPage from '../subjects/SubjectsPage.tsx'
import CurriculumPage from '../curriculum/CurriculumPage.tsx'
import BatchesPage from '../batches/BatchesPage.tsx'
import SectionsPage from '../sections/SectionsPage.tsx'
import StructureRecordsPage from '../structure/StructureRecordsPage.tsx'
import AcademicCalendarPage from '../calendar/AcademicCalendarPage.tsx'
import { type AcademicPage } from './academicOverviewModel.ts'
import { hasAcademicCatalogueReadAccess } from './useAcademicOverview.ts'
import '../styles/overview.css'
import AcademicJourney from '../navigation/AcademicJourney.tsx'
import StudentEnrollmentPage from '../registration/StudentEnrollmentPage.tsx'
import { calendarDestinations, calendarTabFor } from '../navigation/academicCalendarNavigation.ts'

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
  function openRecords(entity?: AcademicEntity, create = false) {
    setRequest({ entity, create })
    props.onNavigate(
      entity === 'departments' || entity === 'programs'
        ? entity
        : entity === 'courses'
          ? 'subjects'
          : entity === 'academic_years'
            ? 'years'
            : 'records',
    )
  }
  const structureContext = {
    accessToken: props.accessToken,
    identity: props.identity,
    institutionId: props.institutionId,
    canReadCatalogues: props.canReadCatalogues,
  }
  if (props.page === 'cohorts')
    return <BatchesPage {...structureContext} onOverview={() => props.onNavigate('overview')} />
  if (props.page === 'sections')
    return (
      <SectionsPage
        {...structureContext}
        onOverview={() => props.onNavigate('overview')}
        onEnrollment={() => props.onNavigate('enrollments')}
      />
    )
  if (props.page === 'enrollments')
    return <StudentEnrollmentPage context={structureContext} onBack={() => props.onNavigate('sections')} />
  if (props.page === 'curriculum' || props.page.startsWith('curriculum-'))
    return (
      <CurriculumPage
        accessToken={props.accessToken}
        identity={props.identity}
        institutionId={props.institutionId}
        canReadCatalogues={props.canReadCatalogues}
        initialTab={props.page === 'curriculum-subjects' ? 'mapping' : 'list'}
        activeTab={
          props.page === 'curriculum-subjects'
            ? 'subjects'
            : props.page === 'curriculum-options'
              ? 'options'
              : props.page === 'curriculum-history'
                ? 'history'
                : props.page === 'curriculum-existing'
                  ? 'existing'
                  : 'versions'
        }
        onTabChange={(tab) =>
          props.onNavigate(
            tab === 'subjects'
              ? 'curriculum-subjects'
              : tab === 'options'
                ? 'curriculum-options'
                : tab === 'history'
                  ? 'curriculum-history'
                  : tab === 'existing'
                    ? 'curriculum-existing'
                    : 'curriculum-versions',
          )
        }
        onOverview={() => props.onNavigate('overview')}
      />
    )
  if (props.page === 'program-semesters' || props.page === 'offerings')
    return (
      <StructureRecordsPage
        key={props.page}
        context={structureContext}
        entity={props.page === 'program-semesters' ? 'program_semesters' : 'academic_offerings'}
        onOverview={() => props.onNavigate('overview')}
      />
    )
  if (calendarTabFor(props.page))
    return (
      <AcademicCalendarPage
        accessToken={props.accessToken}
        identity={props.identity}
        institutionId={props.institutionId}
        canReadCatalogues={props.canReadCatalogues}
        initialTab="years"
        activeTab={calendarTabFor(props.page)}
        onTabChange={(tab) => props.onNavigate(calendarDestinations[tab])}
        createInitially={request.entity === 'academic_years' && request.create}
        onCreateHandled={() => setRequest({ create: false })}
        onOverview={() => props.onNavigate('overview')}
      />
    )
  if (props.page === 'departments' || props.page === 'programs' || props.page === 'subjects') {
    const Page =
      props.page === 'departments' ? DepartmentsPage : props.page === 'programs' ? ProgramsPage : SubjectsPage
    return (
      <Page
        accessToken={props.accessToken}
        identity={props.identity}
        institutionId={props.institutionId}
        canReadCatalogues={props.canReadCatalogues}
        createInitially={request.entity === (props.page === 'subjects' ? 'courses' : props.page) && request.create}
        onCreateHandled={() => setRequest({ create: false })}
        onOverview={() => props.onNavigate('overview')}
      />
    )
  }
  if (props.page === 'records' && props.canReadCatalogues)
    return (
      <section className="academic-workspace academic-existing-records">
        <button type="button" className="academic-back-button" onClick={() => props.onNavigate('overview')}>
          Back to Academic Setup overview
        </button>
        <h1>Existing Academic Catalogues</h1>
        <p className="academic-information">
          <Info aria-hidden="true" /> These record workflows retain the existing data model and permissions.
        </p>
        <AcademicSetup initialEntity={request.entity} createInitially={request.create} />
      </section>
    )
  return (
    <AcademicOverviewSession
      {...props}
      page={props.page === 'records' ? 'overview' : props.page}
      onOpenRecords={openRecords}
    />
  )
}
