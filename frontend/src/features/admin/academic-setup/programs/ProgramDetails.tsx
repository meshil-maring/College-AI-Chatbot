import type { DegreeProgram, Department } from '../../../../types/academicSetup.ts'
import { ProgramBadge } from './ProgramRow.tsx'

export default function ProgramDetails({ record, departments }: { record: DegreeProgram; departments?: Department[] }) {
  const department = departments?.find((item) => item.department_id === record.department_id)
  const details = [
    ['Program Code', record.code],
    ['Department', department ? `${department.name} (${department.code})` : 'Unavailable'],
    ['Degree Type', record.degree_type],
    ['Duration', `${record.duration_years} ${record.duration_years === 1 ? 'Year' : 'Years'}`],
    ['Total Credits', record.total_credits ?? 'Not specified'],
    ['Description', record.description || 'No description provided.'],
  ]
  return (
    <div className="program-details">
      <h3>{record.name}</h3>
      <ProgramBadge active={record.is_active} />
      <dl>
        {details.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
