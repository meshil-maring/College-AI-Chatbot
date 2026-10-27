import { useState } from 'react'
import { ArrowRight, ChevronRight, Clock3, Link2, Search } from 'lucide-react'
import type { AcademicCatalogue, AcademicEntity } from '../../../../types/academicSetup.ts'
import AcademicManagementCard from './AcademicManagementCard.tsx'
import AcademicQuickLinks from './AcademicQuickLinks.tsx'
import {
  allAcademicAreas,
  getAcademicArea,
  managementRows,
  sampleActivities,
  summaryPages,
  type AcademicPage,
} from './academicOverviewModel.ts'
import { overviewRecords, searchAcademicRecords } from './useAcademicOverview.ts'

interface Props {
  catalogue?: AcademicCatalogue
  busy: boolean
  loading: boolean
  search: string
  onClearSearch: () => void
  onNavigate: (page: AcademicPage) => void
  onCreate: (entity: AcademicEntity) => void
  onOpenRecords: (entity: AcademicEntity) => void
}

export default function AcademicOverview({
  catalogue,
  busy,
  loading,
  search,
  onClearSearch,
  onNavigate,
  onCreate,
  onOpenRecords,
}: Props) {
  const [allActivity, setAllActivity] = useState(false)
  const normalized = search
    .trim()
    .toLowerCase()
    .replace(/curricula\b/g, 'curriculum')
  const matchingRecords = normalized ? searchAcademicRecords(catalogue, normalized) : []
  const matches = allAcademicAreas.filter((area) =>
    `${area.title} ${area.description}`.toLowerCase().includes(normalized),
  )
  return (
    <>
      <section className="academic-summary-grid" aria-label="Academic summary" aria-busy={loading}>
        {summaryPages.map((page) => {
          const area = getAcademicArea(page)!
          const records = overviewRecords(catalogue, area.entity)
          const count =
            page === 'departments' || page === 'programs'
              ? records?.filter((record) => record.is_active).length
              : records?.length
          const label =
            page === 'departments'
              ? 'Active departments'
              : page === 'programs'
                ? 'Active programs'
                : page === 'subjects'
                  ? 'Total subjects'
                  : 'Configured years'
          return (
            <button type="button" key={page} className="academic-summary-card" onClick={() => onNavigate(page)}>
              <span className="academic-summary-icon">
                <area.icon aria-hidden="true" />
              </span>
              <span className="academic-summary-copy">
                <span>{area.title}</span>
                <strong className={loading ? 'academic-count-skeleton' : undefined}>{count ?? '—'}</strong>
                <small>{loading ? 'Loading…' : count === undefined ? 'Unavailable' : label}</small>
              </span>
              <ChevronRight aria-hidden="true" />
            </button>
          )
        })}
      </section>
      <section id="academic-overview-results" aria-label="Academic management areas">
        {normalized ? (
          <>
            <p role="status" className="academic-search-status">
              {matches.length} areas and {matchingRecords.length} available records match “{search.trim()}”
            </p>
            {matches.length ? (
              <div className="academic-search-grid">
                {matches.map((area) => (
                  <AcademicManagementCard key={area.page} area={area} catalogue={catalogue} onNavigate={onNavigate} />
                ))}
              </div>
            ) : !matchingRecords.length ? (
              <div className="academic-empty-state">
                <Search aria-hidden="true" />
                <h2>No academic areas found</h2>
                <p>Try a department, program, subject, curriculum, or calendar term.</p>
                <button type="button" className="academic-secondary-button" onClick={onClearSearch}>
                  Clear search
                </button>
              </div>
            ) : null}
            {matchingRecords.length > 0 && (
              <div className="academic-record-search-results">
                <h2>Available records</h2>
                <ul>
                  {matchingRecords.map((record) => (
                    <li key={`${record.entity}-${record.code}`}>
                      <button type="button" onClick={() => onOpenRecords(record.entity)}>
                        <span>
                          <strong>{record.name}</strong>
                          <small>
                            {record.title} · {record.code}
                          </small>
                        </span>
                        <ArrowRight aria-hidden="true" />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        ) : (
          <div className="academic-management-rows">
            {managementRows.map((row, index) => (
              <div className={`academic-management-row academic-row-${row.length}`} key={index}>
                {row.map((area) => (
                  <AcademicManagementCard key={area.page} area={area} catalogue={catalogue} onNavigate={onNavigate} />
                ))}
              </div>
            ))}
          </div>
        )}
      </section>
      <div className="academic-bottom-grid">
        <section className="academic-bottom-panel" aria-labelledby="academic-activity-heading">
          <div className="academic-panel-heading">
            <Clock3 aria-hidden="true" />
            <h2 id="academic-activity-heading">Recent Activities</h2>
            <span className="academic-badge">Sample</span>
            <button type="button" onClick={() => setAllActivity(!allActivity)} aria-expanded={allActivity}>
              {allActivity ? 'Show less' : 'View all'}
              <ChevronRight aria-hidden="true" />
            </button>
          </div>
          <p className="academic-panel-note">Illustrative examples · Activity feed not connected</p>
          <ul className="academic-activity-list">
            {sampleActivities.slice(0, allActivity ? undefined : 4).map((activity, index) => (
              <li key={activity}>
                <span className={`academic-activity-dot academic-dot-${index % 3}`} />
                <span>{activity}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="academic-bottom-panel" aria-labelledby="academic-links-heading">
          <div className="academic-panel-heading">
            <Link2 aria-hidden="true" />
            <h2 id="academic-links-heading">Quick Links</h2>
          </div>
          <p className="academic-panel-note">Available actions follow your permissions. New areas await integration.</p>
          <AcademicQuickLinks catalogue={catalogue} busy={busy} onCreate={onCreate} />
        </section>
      </div>
      <p className="academic-footer-note">
        <ArrowRight aria-hidden="true" /> Academic Terms define dates. Program Semesters define progression.
      </p>
    </>
  )
}
