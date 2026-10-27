import type { CurriculumState } from '../useCurriculum.ts'
import { mappingCredits } from '../curriculumModel.ts'

export default function ProgramOverview({ state }: { state: CurriculumState }) {
  const program = state.selected
  if (!program) return null
  const department = state.catalogue?.records.departments?.find((item) => item.department_id === program.department_id)
  const credits = state.selectedLinks ? mappingCredits(state.selectedLinks, state.courses) : undefined
  const fields = [
    ['Program', `${program.name} (${program.code})`],
    ['Department', department?.name ?? 'Unavailable'],
    ['Degree', program.degree_type],
    ['Duration', `${program.duration_years} years`],
    ['Subject mappings', state.selectedLinks?.length ?? 'Unavailable'],
    ['Mapped credits', credits ?? 'Unavailable'],
    ['Curriculum version', 'Not connected'],
    ['Description', program.description || 'No program description provided.'],
  ]
  return (
    <dl className="curriculum-overview">
      {fields.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}
