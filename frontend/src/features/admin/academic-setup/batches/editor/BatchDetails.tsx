import { batchStatuses, type BatchRecord } from '../batchModel.ts'
import type { BatchesState } from '../useBatches.ts'

export default function BatchDetails({ record, state }: { record: BatchRecord; state: BatchesState }) {
  const program = state.programs.find((item) => item.id === record.programId)
  const items = [
    ['Batch Name', record.name],
    ['Batch Code', record.code],
    ['Program', program?.name],
    ['Curriculum Version', state.curricula.find((item) => item.id === record.curriculumId)?.version ?? 'Unavailable'],
    ['Academic Year', state.years.find((year) => year.academic_year_id === record.academicYear)?.name ?? 'Unavailable'],
    ['Start Year', record.startYear],
    ['End Year', record.endYear],
    ['Student Count', record.studentCount?.toLocaleString('en-IN') ?? 'Unavailable'],
    ['Expected Student Count', record.expectedCount || 'Not specified'],
    ['Description', record.description || 'No description provided'],
    ['Status', batchStatuses.find((item) => item.value === record.status)?.label],
  ]
  return (
    <dl className="batch-details">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}
