import { BookOpenText, ChevronRight, Info, Wand2 } from 'lucide-react'
import type { AcademicEntity } from '../../../../types/academicSetup.ts'
import AcademicOverview from './AcademicOverview.tsx'
import AcademicQuickActions from './AcademicQuickActions.tsx'
import type { AcademicPage } from './academicOverviewModel.ts'
import { useAcademicStructure } from '../structure/useAcademicStructure.ts'

interface Props {
  search: string
  onNavigate: (page: AcademicPage) => void
  onClearSearch: () => void
}

export default function AcademicOverviewSession({
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
  return (
    <div className="academic-workspace">
      <nav className="academic-breadcrumbs" aria-label="Breadcrumb">
        <span>Home</span>
        <ChevronRight aria-hidden="true" />
        <button type="button" onClick={() => onNavigate('overview')}>
          Academic Setup
        </button>
        <ChevronRight aria-hidden="true" />
        <span aria-current="page">Overview</span>
      </nav>
      <header className="academic-page-header">
        <div>
          <h1>Academic Setup</h1>
          <p>Manage your institution’s academic structure, programs, curricula, and calendar.</p>
        </div>
        <div className="academic-header-actions">
          <button type="button" className="academic-secondary-button" onClick={() => onNavigate('guide')}>
            <BookOpenText aria-hidden="true" /> User Guide
          </button>
          <button type="button" className="academic-secondary-button" onClick={() => onNavigate('quick-setup')}>
            <Wand2 aria-hidden="true" /> Quick Setup
          </button>
          <AcademicQuickActions
            catalogue={catalogue}
            structure={structure}
            onNavigate={onNavigate}
            busy={busy}
            onCreate={(entity) => onOpenRecords(entity, true)}
          />
        </div>
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
    </div>
  )
}
