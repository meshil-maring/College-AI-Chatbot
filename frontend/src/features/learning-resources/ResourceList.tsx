import { ArrowUpRight, BookOpen, FileText } from 'lucide-react'
import type { LearningResource, ResourceRevision } from '../../types/learningResources.ts'
import { AudienceBadge, IndexBadge, RevisionBadge } from './ResourceBadges.tsx'
import { indexState, typeLabel } from './resourcePresentation.ts'

export default function ResourceList({
  rows,
  onOpen,
}: {
  rows: (LearningResource | ResourceRevision)[]
  onOpen: (row: LearningResource | ResourceRevision) => void
}) {
  return (
    <div className="lr-list">
      <div className="lr-list-head" aria-hidden="true">
        <span>Resource</span>
        <span>Audience</span>
        <span>Status</span>
        <span>Details</span>
      </div>
      <ul aria-label="Learning resource results">
        {rows.map((row) => {
          const revision = 'revision_id' in row
          return (
            <li key={revision ? row.revision_id : row.knowledge_source_id}>
              <div className="lr-record-title">
                <span className="lr-resource-icon">
                  <BookOpen size={20} aria-hidden="true" />
                </span>
                <div>
                  <button type="button" className="lr-title-link" onClick={() => onOpen(row)}>
                    {row.title}
                  </button>
                  <p className="lr-help">
                    {typeLabel(row.source_type)}
                    {revision ? ` · Revision ${row.revision_number}` : ''}
                  </p>
                  {row.description && <p className="lr-record-description">{row.description}</p>}
                  <p className="lr-file-count">
                    <FileText size={14} aria-hidden="true" />
                    {row.documents.length} file{row.documents.length === 1 ? '' : 's'}
                  </p>
                </div>
              </div>
              <div className="lr-record-audience">
                <span className="lr-mobile-label">Audience</span>
                <AudienceBadge resource={row} />
              </div>
              <div className="lr-record-status">
                <span className="lr-mobile-label">Status</span>
                <RevisionBadge status={revision ? row.lifecycle_status : 'published'} />
                {row.documents.length > 0 && <IndexBadge status={indexState(row)} />}
              </div>
              <button
                type="button"
                className="lr-secondary lr-open"
                aria-label={`View ${row.title}`}
                onClick={() => onOpen(row)}
              >
                View <ArrowUpRight size={16} aria-hidden="true" />
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
