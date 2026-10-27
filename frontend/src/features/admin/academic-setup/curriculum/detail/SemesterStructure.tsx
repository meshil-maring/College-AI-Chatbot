import { ChevronRight, Plus } from 'lucide-react'
import type { CurriculumState } from '../useCurriculum.ts'
import { mappingCredits, semesterGroups } from '../curriculumModel.ts'
import MappingTable, { type MappingActions } from './MappingTable.tsx'

export default function SemesterStructure({ state, ...actions }: { state: CurriculumState } & MappingActions) {
  if (!state.selectedLinks)
    return <p className="curriculum-detail-note">Subject mappings are unavailable for this account.</p>
  const groups = semesterGroups(state.selectedLinks, state.semesters)
  return (
    <div className="curriculum-semesters">
      <p className="curriculum-detail-note">
        Existing dated academic terms. Program progression semesters and curriculum versions are not connected.
      </p>
      {!groups.length && <p className="curriculum-detail-note">No subject mappings for this program yet.</p>}
      {groups.map((group, index) => {
        const credits = mappingCredits(group.links, state.courses)
        return (
          <details className="curriculum-semester" key={`${state.selected?.program_id}-${group.id}`} open={index === 0}>
            <summary>
              <ChevronRight aria-hidden="true" />
              <strong>{group.label}</strong>
              <span>
                {group.links.length} Subjects<span aria-hidden="true"> | </span>
                {credits == null ? 'Credits unavailable' : `${credits} Credits`}
              </span>
            </summary>
            {group.semester && (
              <p className="curriculum-term-name">
                {group.semester.name} ({group.semester.code})
              </p>
            )}
            <MappingTable state={state} links={group.links} {...actions} />
            <footer>
              <button
                type="button"
                className="curriculum-outline-button"
                disabled={
                  !state.canAdd ||
                  Boolean(group.semester && !state.parents?.semesters.has(group.semester.semester_id)) ||
                  Boolean(group.id !== 'unassigned' && !group.semester)
                }
                onClick={() => actions.onAdd(group.semester?.semester_id)}
              >
                <Plus aria-hidden="true" />
                Add Subject
              </button>
            </footer>
          </details>
        )
      })}
      {!groups.length && (
        <button
          type="button"
          className="curriculum-outline-button"
          disabled={!state.canAdd}
          onClick={() => actions.onAdd()}
        >
          <Plus aria-hidden="true" />
          Add Subject
        </button>
      )}
    </div>
  )
}
