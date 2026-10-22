import type { AcademicPackageCatalogue } from '../../types/academicPackages.ts'
import { find, label, rows, value } from './packagePresentation.ts'

export function PackageSubjects({ data, packageId }: { data: AcademicPackageCatalogue; packageId: string }) {
  const selected = find(data, 'packages', packageId)
  if (!selected) return null
  const semester = value(selected, 'study_semester')
  const subjects = rows(data, 'curriculum_subjects').filter(
    (row) =>
      value(row, 'curriculum_id') === value(selected, 'curriculum_id') && value(row, 'study_semester') === semester,
  )
  const members = new Set(
    rows(data, 'package_subjects')
      .filter((row) => value(row, 'package_id') === packageId)
      .map((row) => value(row, 'curriculum_subject_id')),
  )
  const assigned = subjects.filter((row) => row.is_core === true || members.has(value(row, 'curriculum_subject_id')))
  return (
    <div aria-label="Complete package subjects">
      <p className="package-helper">
        Every listed subject is assigned together. Shared core subjects are included once.
      </p>
      {assigned.length ? (
        <ul className="package-subject-list">
          {assigned.map((row) => (
            <li key={value(row, 'curriculum_subject_id')}>{label(data, 'curriculum_subjects', row)}</li>
          ))}
        </ul>
      ) : (
        <p className="package-helper">No subject membership is available for this package.</p>
      )}
    </div>
  )
}
