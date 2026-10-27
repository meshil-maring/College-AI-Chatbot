import type { ProgramCourse } from '../../../../../types/academicSetup.ts'
import type { CurriculumState } from '../useCurriculum.ts'
import MappingRow from './MappingRow.tsx'

export interface MappingActions {
  onAdd: (semesterId?: string) => void
  onEdit: (link: ProgramCourse) => void
  onStatus: (link: ProgramCourse) => void
}
export default function MappingTable({
  state,
  links,
  onEdit,
  onStatus,
}: {
  state: CurriculumState
  links: ProgramCourse[]
} & Pick<MappingActions, 'onEdit' | 'onStatus'>) {
  return (
    <div className="curriculum-table-scroll">
      <table className="curriculum-mapping-table">
        <caption className="sr-only">Subject mappings for {state.selected?.name}</caption>
        <thead>
          <tr>
            {['Code', 'Subject Name', 'Type', 'L', 'T', 'P', 'Credits', 'Status', 'Actions'].map((label) => (
              <th scope="col" key={label}>
                <abbr
                  title={
                    label === 'L'
                      ? 'Lecture hours'
                      : label === 'T'
                        ? 'Tutorial hours'
                        : label === 'P'
                          ? 'Practical hours'
                          : label
                  }
                >
                  {label}
                </abbr>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {links.map((link) => (
            <MappingRow
              key={link.program_course_id}
              link={link}
              course={state.courses?.find((course) => course.course_id === link.course_id)}
              editable={state.manageable && !state.busy}
              onEdit={onEdit}
              onStatus={onStatus}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}
