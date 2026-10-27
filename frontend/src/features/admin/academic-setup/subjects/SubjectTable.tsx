import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import type { Course } from '../../../../types/academicSetup.ts'
import type { SubjectsState } from './useSubjects.ts'
import { SUBJECT_PAGE_SIZE, type SubjectSortField } from './subjectModel.ts'
import SubjectRow from './SubjectRow.tsx'
import SubjectPagination from './SubjectPagination.tsx'
import SubjectListState from './SubjectListState.tsx'

interface Props {
  state: SubjectsState
  onCreate: () => void
  onOpen: (mode: 'view' | 'edit', record: Course) => void
  onStatus: (record: Course) => void
}
const columns: [SubjectSortField, string][] = [
  ['code', 'Subject Code'],
  ['name', 'Subject Name'],
]
export default function SubjectTable({ state, onCreate, onOpen, onStatus }: Props) {
  return (
    <section className="subject-table-panel" aria-label="Subject records" aria-busy={state.loading}>
      {state.loading && (
        <p className="sr-only" role="status">
          Loading subjects…
        </p>
      )}
      <table className="subject-table">
        <caption className="sr-only">Subjects in your institution</caption>
        <thead>
          <tr>
            {columns.map(([field, label]) => {
              const selected = state.sort.startsWith(`${field}-`)
              const descending = state.sort.endsWith('desc')
              const Icon = selected ? (descending ? ArrowDown : ArrowUp) : ArrowUpDown
              return (
                <th key={field} scope="col" aria-sort={selected ? (descending ? 'descending' : 'ascending') : 'none'}>
                  <button
                    type="button"
                    disabled={!state.records}
                    onClick={() => state.setSort(`${field}-${selected && !descending ? 'desc' : 'asc'}`)}
                  >
                    {label}
                    <Icon aria-hidden="true" />
                  </button>
                </th>
              )
            })}
            {['Department', 'Semester', 'Type', 'Credits', 'L', 'T', 'P'].map((label) => (
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
            <th
              scope="col"
              aria-sort={
                state.sort.startsWith('is_active') ? (state.sort.endsWith('desc') ? 'descending' : 'ascending') : 'none'
              }
            >
              <button
                type="button"
                disabled={!state.records}
                onClick={() => state.setSort(state.sort === 'is_active-asc' ? 'is_active-desc' : 'is_active-asc')}
              >
                Status <ArrowUpDown aria-hidden="true" />
              </button>
            </th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {state.loading ? (
            Array.from({ length: SUBJECT_PAGE_SIZE }, (_, i) => (
              <tr className="subject-loading-row" key={i} aria-hidden="true">
                {Array.from({ length: 11 }, (_, j) => (
                  <td key={j}>
                    <span className="subject-skeleton" />
                  </td>
                ))}
              </tr>
            ))
          ) : !state.rows.length ? (
            <tr>
              <td colSpan={11}>
                <SubjectListState state={state} onCreate={onCreate} />
              </td>
            </tr>
          ) : (
            state.rows.map((record, index) => (
              <SubjectRow
                key={record.course_id}
                record={record}
                index={index}
                department={state.departments?.find((item) => item.department_id === record.department_id)}
                assignments={state.assignments}
                editable={state.manageable && !state.busy}
                onOpen={onOpen}
                onStatus={onStatus}
              />
            ))
          )}
        </tbody>
      </table>
      <SubjectPagination state={state} />
    </section>
  )
}
