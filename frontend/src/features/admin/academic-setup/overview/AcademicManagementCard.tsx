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
        <button
          type="button"
          className="academic-arrow"
          aria-label={`Open ${area.title}`}
          onClick={() => onNavigate(area.page)}
        >
          <ArrowRight aria-hidden="true" />
        </button>
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
          <dl className="academic-card-metrics">
            <div>
              <dt>Active</dt>
              <dd>{active}</dd>
            </div>
            <div>
              <dt>Inactive</dt>
              <dd>{records.length - active!}</dd>
            </div>
          </dl>
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
