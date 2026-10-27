import { useState } from 'react'
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

interface Props {
  page: AcademicPage
  search: string
  onNavigate: (page: AcademicPage) => void
  onClearSearch: () => void
}

export default function AcademicWorkspace(props: Props) {
  const { accessToken, user, role } = useAuth()
  if (!accessToken || !user || role !== 'admin' || !user.institution_id)
    return <p role="status">Administrator access is unavailable.</p>
  const identity = JSON.stringify([accessToken, user.user_id, user.institution_id, user.effective_permissions])
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
    return <SectionsPage {...structureContext} onOverview={() => props.onNavigate('overview')} />
  if (props.page === 'curriculum' || props.page === 'curriculum-versions' || props.page === 'curriculum-subjects')
    return (
      <CurriculumPage
        key={props.page}
        accessToken={props.accessToken}
        identity={props.identity}
        institutionId={props.institutionId}
        canReadCatalogues={props.canReadCatalogues}
        initialTab={props.page === 'curriculum-subjects' ? 'mapping' : 'list'}
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
  if (props.page === 'calendar' || props.page === 'years' || props.page === 'terms')
    return (
      <AcademicCalendarPage
        key={props.page}
        accessToken={props.accessToken}
        identity={props.identity}
        institutionId={props.institutionId}
        canReadCatalogues={props.canReadCatalogues}
        initialTab={props.page === 'terms' ? 'semesters' : 'years'}
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
