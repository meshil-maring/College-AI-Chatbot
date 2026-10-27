import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import type { DegreeProgram } from '../../../../types/academicSetup.ts'
import type { ProgramsState } from './usePrograms.ts'
import { PROGRAM_PAGE_SIZE, type ProgramSortField } from './programModel.ts'
import ProgramRow from './ProgramRow.tsx'
import ProgramPagination from './ProgramPagination.tsx'
import ProgramListState from './ProgramListState.tsx'

interface Props {
  state: ProgramsState
  onCreate: () => void
  onOpen: (mode: 'view' | 'edit', record: DegreeProgram) => void
  onStatus: (record: DegreeProgram) => void
}
const columns: [ProgramSortField, string][] = [
  ['name', 'Program Name'],
  ['code', 'Code'],
  ['department', 'Department'],
  ['degree_type', 'Degree Type'],
  ['duration_years', 'Duration'],
  ['total_credits', 'Credits'],
  ['is_active', 'Status'],
]
export default function ProgramTable({ state, onCreate, onOpen, onStatus }: Props) {
  return (
    <section className="program-table-panel" aria-label="Program records" aria-busy={state.loading}>
      {state.loading && (
        <p className="sr-only" role="status">
          Loading programs…
        </p>
      )}
      <table className="program-table">
        <caption className="sr-only">Programs in your institution</caption>
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
                    disabled={!state.records || (field === 'department' && !state.departments)}
                    onClick={() => state.setSort(`${field}-${selected && !descending ? 'desc' : 'asc'}`)}
                  >
                    {label}
                    <Icon aria-hidden="true" />
                  </button>
                </th>
              )
            })}
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {state.loading ? (
            Array.from({ length: PROGRAM_PAGE_SIZE }, (_, i) => (
              <tr className="program-loading-row" key={i} aria-hidden="true">
                {Array.from({ length: 8 }, (_, j) => (
                  <td key={j}>
                    <span className="program-skeleton" />
                  </td>
                ))}
              </tr>
            ))
          ) : !state.rows.length ? (
            <tr>
              <td colSpan={8}>
                <ProgramListState state={state} onCreate={onCreate} />
              </td>
            </tr>
          ) : (
            state.rows.map((record, index) => (
              <ProgramRow
                key={record.program_id}
                record={record}
                index={index}
                department={state.departments?.find((item) => item.department_id === record.department_id)}
                editable={state.manageable && !state.busy}
                onOpen={onOpen}
                onStatus={onStatus}
              />
            ))
          )}
        </tbody>
      </table>
      <ProgramPagination state={state} />
    </section>
  )
}
