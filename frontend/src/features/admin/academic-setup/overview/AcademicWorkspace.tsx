import { useState } from 'react'
import { ChevronRight, Info } from 'lucide-react'
import { useAuth } from '../../../auth/session/AuthProvider.tsx'
import type { AcademicEntity } from '../../../../types/academicSetup.ts'
import AcademicSetup from '../AcademicSetup.tsx'
import AcademicOverview from './AcademicOverview.tsx'
import AcademicAreaView from './AcademicAreaView.tsx'
import AcademicQuickActions from './AcademicQuickActions.tsx'
import DepartmentsPage from '../departments/DepartmentsPage.tsx'
import ProgramsPage from '../programs/ProgramsPage.tsx'
import AcademicCalendarPage from '../calendar/AcademicCalendarPage.tsx'
import { getAcademicArea, type AcademicPage } from './academicOverviewModel.ts'
import { hasAcademicCatalogueReadAccess, useAcademicOverview } from './useAcademicOverview.ts'
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
      entity === 'departments' || entity === 'programs' ? entity : entity === 'academic_years' ? 'years' : 'records',
    )
  }
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
  if (props.page === 'departments' || props.page === 'programs') {
    const Page = props.page === 'departments' ? DepartmentsPage : ProgramsPage
    return (
      <Page
        accessToken={props.accessToken}
        identity={props.identity}
        institutionId={props.institutionId}
        canReadCatalogues={props.canReadCatalogues}
        createInitially={request.entity === props.page && request.create}
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

function AcademicOverviewSession({
  page,
  search,
  onNavigate,
  onClearSearch,
  accessToken,
  identity,
  institutionId,
  canReadCatalogues,
  onOpenRecords,
}: Props & {
  accessToken: string
  identity: string
  institutionId: string
  canReadCatalogues: boolean
  onOpenRecords: (entity?: AcademicEntity, create?: boolean) => void
}) {
  const { query, catalogue, error, loading } = useAcademicOverview(
    accessToken,
    identity,
    institutionId,
    canReadCatalogues,
  )
  const busy = query.isFetching || Boolean(error) || !catalogue
  const title = page === 'overview' ? 'Academic Setup' : (getAcademicArea(page)?.title ?? 'Academic Setup')
  return (
    <div className="academic-workspace">
      <nav className="academic-breadcrumbs" aria-label="Breadcrumb">
        <span>Home</span>
        <ChevronRight aria-hidden="true" />
        <button type="button" onClick={() => onNavigate('overview')}>
          Academic Setup
        </button>
        <ChevronRight aria-hidden="true" />
        <span aria-current="page">{page === 'overview' ? 'Overview' : title}</span>
      </nav>
      <header className="academic-page-header">
        <div>
          <h1>{title}</h1>
          <p>Manage your institution’s academic structure, programs, curricula, and calendar.</p>
        </div>
        <AcademicQuickActions
          key={page}
          catalogue={catalogue}
          busy={busy}
          onCreate={(entity) => onOpenRecords(entity, true)}
        />
      </header>
      <p className="academic-information" role={canReadCatalogues ? undefined : 'status'}>
        <Info aria-hidden="true" />
        <span>
          {canReadCatalogues
            ? 'New academic areas are design previews. Counts use available catalogue data; activity examples are samples.'
            : 'Design preview · Your account does not have academic catalogue access. Counts and record actions are unavailable.'}
        </span>
      </p>
      {loading && (
        <p className="sr-only" role="status">
          Loading Academic Setup…
        </p>
      )}
      {error && (
        <div className="academic-request-error" role="alert">
          <p>{error}</p>
          <button
            type="button"
            className="academic-secondary-button"
            disabled={query.isFetching}
            onClick={() => void query.refetch()}
          >
            Retry
          </button>
        </div>
      )}
      {page === 'overview' ? (
        <AcademicOverview
          catalogue={catalogue}
          busy={busy}
          loading={loading}
          search={search}
          onClearSearch={onClearSearch}
          onNavigate={onNavigate}
          onCreate={(entity) => onOpenRecords(entity, true)}
          onOpenRecords={onOpenRecords}
        />
      ) : (
        <AcademicAreaView
          page={page}
          catalogue={catalogue}
          busy={busy}
          onNavigate={onNavigate}
          onOpenRecords={onOpenRecords}
        />
      )}
    </div>
  )
}
