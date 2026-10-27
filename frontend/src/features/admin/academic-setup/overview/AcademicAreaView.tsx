import { ArrowLeft, ArrowRight, Database, LockKeyhole } from 'lucide-react'
import type { AcademicCatalogue, AcademicEntity } from '../../../../types/academicSetup.ts'
import { getAcademicArea, type AcademicPage } from './academicOverviewModel.ts'
import { overviewRecords } from './useAcademicOverview.ts'

interface Props {
  page: AcademicPage
  catalogue?: AcademicCatalogue
  busy: boolean
  onNavigate: (page: AcademicPage) => void
  onOpenRecords: (entity?: AcademicEntity) => void
}

export default function AcademicAreaView({ page, catalogue, busy, onNavigate, onOpenRecords }: Props) {
  const area = getAcademicArea(page)
  if (!area) return null
  const records = overviewRecords(catalogue, area.entity)
  return (
    <section className="academic-area-view" aria-label={area.title}>
      <button type="button" className="academic-back-button" onClick={() => onNavigate('overview')}>
        <ArrowLeft aria-hidden="true" /> Back to overview
      </button>
      <div className="academic-area-intro">
        <span className="academic-icon">
          <area.icon aria-hidden="true" />
        </span>
        <div>
          <h2>{area.title}</h2>
          <p>{area.description}</p>
        </div>
      </div>
      {area.children && (
        <div className="academic-area-children">
          {area.children.map((child) => {
            const childArea = getAcademicArea(child)!
            return (
              <button type="button" key={child} onClick={() => onNavigate(child)}>
                <childArea.icon aria-hidden="true" />
                <span>
                  <strong>{childArea.title}</strong>
                  <small>{childArea.description}</small>
                </span>
                <ArrowRight aria-hidden="true" />
              </button>
            )
          })}
        </div>
      )}
      <div className="academic-area-guidance">
        <LockKeyhole aria-hidden="true" />
        <p>{area.note}</p>
      </div>
      {area.statuses && (
        <div className="academic-state-legend">
          <span>Proposed states</span>
          {area.statuses.map((status) => (
            <span className={`academic-status academic-status-${status.toLowerCase()}`} key={status}>
              {status}
            </span>
          ))}
          <small>Available transitions will follow the connected service.</small>
        </div>
      )}
      <div className="academic-empty-state">
        <Database aria-hidden="true" />
        <h3>{records ? 'Existing catalogue available' : 'This area is awaiting integration'}</h3>
        <p>
          {records
            ? 'Open the existing record workflow to view and manage permitted records.'
            : 'This design defines the academic area. Records, counts, and write actions are not connected yet.'}
        </p>
        {records && (
          <button
            type="button"
            className="academic-primary-button"
            disabled={busy}
            onClick={() => onOpenRecords(area.entity)}
          >
            Open existing catalogue <ArrowRight aria-hidden="true" />
          </button>
        )}
      </div>
      {(page === 'sections' || page === 'offerings') && (
        <p className="academic-panel-note">
          The existing catalogue uses offering-owned sections. It is kept separate from this proposed cohort-based
          section model.
        </p>
      )}
    </section>
  )
}
