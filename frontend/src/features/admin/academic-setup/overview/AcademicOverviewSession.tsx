import { ChevronRight, Info } from 'lucide-react'
import type { AcademicEntity } from '../../../../types/academicSetup.ts'
import AcademicOverview from './AcademicOverview.tsx'
import AcademicAreaView from './AcademicAreaView.tsx'
import AcademicQuickActions from './AcademicQuickActions.tsx'
import { getAcademicArea, type AcademicPage } from './academicOverviewModel.ts'
import { useAcademicStructure } from '../structure/useAcademicStructure.ts'

interface Props {
  page: AcademicPage
  search: string
  onNavigate: (page: AcademicPage) => void
  onClearSearch: () => void
}

export default function AcademicOverviewSession({
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
  const state = useAcademicStructure({ accessToken, identity, institutionId, canReadCatalogues })
  const { catalogue, structure, error, loading } = state
  const busy = state.busy || !catalogue
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
          structure={structure}
          onNavigate={onNavigate}
          busy={busy}
          onCreate={(entity) => onOpenRecords(entity, true)}
        />
      </header>
      <p className="academic-information" role={canReadCatalogues ? undefined : 'status'}>
        <Info aria-hidden="true" />
        <span>
          {canReadCatalogues
            ? 'Counts, relationships and recent activity use saved academic records for your institution.'
            : 'Your account does not have academic catalogue access. Counts and record actions are unavailable.'}
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
            disabled={state.refreshing}
            onClick={() => void state.refresh()}
          >
            Retry
          </button>
        </div>
      )}
      {page === 'overview' ? (
        <AcademicOverview
          catalogue={catalogue}
          structure={structure}
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
