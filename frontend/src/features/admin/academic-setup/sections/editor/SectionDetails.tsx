import { sectionStatuses, type SectionRecord } from '../sectionModel.ts'
import type { SectionsState } from '../useSections.ts'

export default function SectionDetails({ record, state }: { record: SectionRecord; state: SectionsState }) {
  const batch = state.batches.find((item) => item.id === record.batchId)
  const program = state.programs.find((item) => item.id === batch?.programId)
  const items = [
    ['Section Name', record.name],
    ['Section Code', record.code],
    ['Batch', batch?.name],
    ['Program', program?.name],
    ['Academic Year', batch?.academicYear],
    [
      'Program Semester',
      state.stages.find((stage) => stage.program_semester_id === record.programSemesterId)?.name ?? 'Unavailable',
    ],
    ['Teaching Term', state.terms.find((term) => term.semester_id === record.semesterId)?.name ?? 'Unavailable'],
    ['Student Count', record.studentCount?.toLocaleString('en-IN') ?? 'Unavailable'],
    ['Maximum Capacity', record.capacity || 'Not specified'],
    ['Description', record.description || 'No description provided'],
    ['Status', sectionStatuses.find((item) => item.value === record.status)?.label],
  ]
  return (
    <dl className="section-details">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}
