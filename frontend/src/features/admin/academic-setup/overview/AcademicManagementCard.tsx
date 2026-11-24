import { ArrowRight } from 'lucide-react'
import type { AcademicCatalogue } from '../../../../types/academicSetup.ts'
import type { StructureCatalogue } from '../../../../types/academicStructure.ts'
import { getAcademicArea, type AcademicArea, type AcademicPage } from './academicOverviewModel.ts'
import { overviewRecords } from './useAcademicOverview.ts'

interface Props {
  area: AcademicArea
  catalogue?: AcademicCatalogue
  structure?: StructureCatalogue
  onNavigate: (page: AcademicPage) => void
}

export default function AcademicManagementCard({ area, catalogue, structure, onNavigate }: Props) {
  const records = area.structureEntity
    ? structure?.records[area.structureEntity]
    : overviewRecords(catalogue, area.entity)
  const active = records?.filter((record) => record.is_active).length
  return (
    <article className="academic-management-card" aria-labelledby={`academic-card-${area.page}`}>
      <div className="academic-card-heading">
        <span className="academic-icon">
          <area.icon aria-hidden="true" />
        </span>
        <h2 id={`academic-card-${area.page}`}>{area.title}</h2>
      </div>
      <p className="academic-card-description">{area.description}</p>
      <div className="academic-card-context">
        {area.children ? (
          area.children.map((page) => (
            <button type="button" key={page} className="academic-child-link" onClick={() => onNavigate(page)}>
              <span>{getAcademicArea(page)!.title}</span>
              {page === 'curriculum-versions' && (
                <span className="academic-version-statuses">
                  <small>Draft</small>
                  <small>Published</small>
                </span>
              )}
              <ArrowRight aria-hidden="true" />
            </button>
          ))
        ) : records ? (
          <AreaMetrics active={active!} total={records.length} />
        ) : (
          <p>{area.note}</p>
        )}
      </div>
      <button type="button" className="academic-manage-button" onClick={() => onNavigate(area.page)}>
        <span>{area.action}</span>
        <ArrowRight aria-hidden="true" />
      </button>
    </article>
  )
}

function AreaMetrics({ active, total }: { active: number; total: number }) {
  const inactive = total - active
  const share = total ? Math.round((active / total) * 100) : 0
  return (
    <div className="academic-card-metrics">
      <p className="academic-card-total">
        <strong>{total}</strong>
        <span>total</span>
      </p>
      <dl>
        <div className="is-active">
          <dt>Active</dt>
          <dd>{active}</dd>
        </div>
        <div>
          <dt>Inactive</dt>
          <dd>{inactive}</dd>
        </div>
      </dl>
      <span className="academic-card-meter" aria-hidden="true">
        <span style={{ width: `${share}%` }} />
      </span>
    </div>
  )
}
