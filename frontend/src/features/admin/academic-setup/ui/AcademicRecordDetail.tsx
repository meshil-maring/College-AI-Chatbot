import { Pencil, Plus } from 'lucide-react'
import type { AcademicEntity, AcademicRecord } from '../../../../types/academicSetup.ts'
import { ACADEMIC_DEFINITIONS } from '../academicSetupDefinitions.ts'
import { find, label, records, usable } from '../academicSetupModel.ts'
import { entityIcons, entitySingular, entityTitles } from '../academicSetupPresentation.ts'
import type { AcademicSetupState } from '../useAcademicSetup.ts'

export default function AcademicRecordDetail({
  state,
  row,
  onNavigate,
}: {
  state: AcademicSetupState
  row: AcademicRecord | undefined
  onNavigate: (entity: AcademicEntity) => void
}) {
  const { data, entity, canManage, busy, formOpen, open } = state
  if (!data || !row)
    return (
      <aside className="academic-panel academic-detail academic-detail-empty">
        <span>Select a record to view its details.</span>
      </aside>
    )
  const Icon = entityIcons[entity]
  const related: AcademicEntity | undefined =
    entity === 'departments'
      ? 'programs'
      : entity === 'academic_years'
        ? 'semesters'
        : entity === 'course_offerings'
          ? 'sections'
          : undefined
  const idKey = ACADEMIC_DEFINITIONS[entity].id
  const children = related ? records(data, related).filter((child) => child[idKey] === row[idKey]) : []
  const active = usable(data, entity, row)
  const fields = ACADEMIC_DEFINITIONS[entity].fields.filter(
    (field) => field.key !== 'description' && field.type !== 'checkbox',
  )
  return (
    <aside className="academic-panel academic-detail" aria-label={`${entitySingular[entity]} details`}>
      <header className="academic-detail-header">
        <span className="academic-detail-icon">
          <Icon aria-hidden="true" />
        </span>
        <div>
          <h2>{String(row.code ?? entitySingular[entity])}</h2>
          <p>{String(row.name ?? label(data, entity, row))}</p>
        </div>
        <span className={`academic-badge ${active ? 'is-active' : 'is-inactive'}`}>
          {active ? 'Active' : row.is_active ? 'Unavailable' : 'Inactive'}
        </span>
        {canManage && (
          <button type="button" className="academic-primary" disabled={busy || formOpen} onClick={() => open(row)}>
            <Pencil aria-hidden="true" />
            Edit {entitySingular[entity]}
          </button>
        )}
      </header>
      <div className="academic-detail-tabs">
        <span aria-current="page">Overview</span>
        {related && data.records[related] !== undefined && (
          <button type="button" disabled={busy || formOpen} onClick={() => onNavigate(related)}>
            {entityTitles[related]}
            <span className="academic-count">{children.length}</span>
          </button>
        )}
      </div>
      <div className="academic-detail-body">
        {entity === 'programs' && (
          <p className="academic-muted">Build this program's subject combinations in Curricula &amp; packages.</p>
        )}
        <dl className="academic-detail-fields">
          {fields.map((field) => {
            const value = row[field.key]
            const parent = field.source && value ? find(data, field.source, value) : undefined
            return (
              <div key={field.key}>
                <dt>{field.label}</dt>
                <dd>
                  {parent
                    ? label(data, field.source!, parent)
                    : value === undefined || value === null || value === ''
                      ? '—'
                      : String(value).replaceAll('_', ' ')}
                </dd>
              </div>
            )
          })}
          <div className="academic-description">
            <dt>Description</dt>
            <dd>{String(row.description || 'No description added.')}</dd>
          </div>
        </dl>
      </div>
      {related && data.records[related] !== undefined && (
        <section className="academic-related">
          <div className="academic-panel-heading">
            <h3>
              <Icon aria-hidden="true" />
              {entity === 'departments'
                ? 'Degree programs in this Department'
                : `${entityTitles[related]} in this ${entitySingular[entity]}`}
              <span className="academic-count">{children.length}</span>
            </h3>
            {data.manageable.includes(related) && (
              <button
                type="button"
                className="academic-primary"
                disabled={busy || formOpen}
                onClick={() => onNavigate(related)}
              >
                <Plus aria-hidden="true" />
                Manage {entityTitles[related]}
              </button>
            )}
          </div>
          {children.length ? (
            <div className="academic-table-scroll">
              <table className="academic-table">
                <thead>
                  <tr>
                    <th scope="col">#</th>
                    <th scope="col">{entitySingular[related]} Name</th>
                    {related === 'programs' && <th scope="col">Duration</th>}
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {children.map((child, index) => (
                    <tr key={String(child[ACADEMIC_DEFINITIONS[related].id])}>
                      <td>{index + 1}</td>
                      <td>
                        {String(child.name ?? label(data, related, child))}
                        <small>{String(child.code ?? '')}</small>
                      </td>
                      {related === 'programs' && (
                        <td>{child.duration_years ? `${child.duration_years} Years` : '—'}</td>
                      )}
                      <td>
                        <span
                          className={`academic-badge ${usable(data, related, child) ? 'is-active' : 'is-inactive'}`}
                        >
                          {usable(data, related, child) ? 'Active' : 'Unavailable'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="academic-empty">No {entityTitles[related].toLowerCase()} linked yet.</p>
          )}
          {related === 'programs' && (
            <p className="academic-related-note">
              Individual subjects are managed in the Subjects step. Build named subject combinations in Curricula &amp;
              packages.
            </p>
          )}
        </section>
      )}
    </aside>
  )
}
