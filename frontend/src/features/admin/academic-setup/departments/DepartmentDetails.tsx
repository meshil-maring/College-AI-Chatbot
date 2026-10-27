import { BookOpen } from 'lucide-react'
import type { AcademicCatalogue, Department } from '../../../../types/academicSetup.ts'
import { departmentPrograms } from './departmentModel.ts'
import { DepartmentBadge } from './DepartmentTable.tsx'

export default function DepartmentDetails({
  record,
  catalogue,
}: {
  record: Department
  catalogue?: AcademicCatalogue
}) {
  const programs = departmentPrograms(catalogue, record.department_id)
  return (
    <div className="department-details">
      <div className="department-identity">
        <span className="department-avatar" aria-hidden="true">
          {record.name.slice(0, 1).toLocaleUpperCase()}
        </span>
        <h3>{record.name}</h3>
      </div>
      <DepartmentBadge active={record.is_active} />
      <dl>
        <dt>Department Code</dt>
        <dd>{record.code}</dd>
        <dt>Description</dt>
        <dd>{record.description || 'No description provided.'}</dd>
      </dl>
      <section aria-labelledby="department-programs-title">
        <h3 id="department-programs-title">Associated programs</h3>
        {programs === undefined ? (
          <div className="department-programs-unavailable">
            <BookOpen aria-hidden="true" />
            <strong>— programs</strong>
            <p>Program data is not connected.</p>
          </div>
        ) : programs.length === 0 ? (
          <p>No associated programs.</p>
        ) : (
          <ul className="department-program-list">
            {programs.map((program) => (
              <li key={program.program_id}>
                <div>
                  <strong>{program.name}</strong>
                  <small>{program.code}</small>
                </div>
                <DepartmentBadge active={program.is_active} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
