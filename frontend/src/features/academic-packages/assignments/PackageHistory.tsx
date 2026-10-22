import type { AcademicPackageCatalogue } from '../../../types/academicPackages.ts'
import { labelForId, rows, value } from '../packagePresentation.ts'

export default function PackageHistory({ data }: { data: AcademicPackageCatalogue }) {
  const history = rows(data, 'history')
  return (
    <section className="package-records" aria-label="Package assignment history">
      {!history.length && <p className="academic-empty">No package assignment history in your academic scope.</p>}
      {history.map((row, index) => (
        <article
          key={value(row, 'revision_id') || `${value(row, 'assignment_id')}:${value(row, 'revision')}:${index}`}
          className="package-record"
        >
          <h3>{value(row, 'action') || `Assignment revision ${value(row, 'revision')}`}</h3>
          {value(row, 'package_id') && <p>{labelForId(data, 'packages', value(row, 'package_id'))}</p>}
          {value(row, 'assignment_id') && <p>{labelForId(data, 'assignments', value(row, 'assignment_id'))}</p>}
          {value(row, 'placement_id') && <p>{labelForId(data, 'placements', value(row, 'placement_id'))}</p>}
          <p>{value(row, 'reason') || 'Initial package assignment'}</p>
          <p className="package-helper">
            {value(row, 'applied_at') || value(row, 'created_at')} {value(row, 'actor_name')}
          </p>
        </article>
      ))}
    </section>
  )
}
