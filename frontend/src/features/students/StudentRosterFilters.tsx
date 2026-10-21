import { RefreshCw, SlidersHorizontal } from 'lucide-react'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import type { FacultyAttendanceAssignment } from '../../services/faculty/facultyAttendanceApi.ts'
import { useStudentWorkspaceApi } from './StudentWorkspaceContext.tsx'

const courseOf = (item: FacultyAttendanceAssignment) => item.section.program?.degree_type?.trim() ?? ''
const branchOf = (item: FacultyAttendanceAssignment) => item.section.program_id ?? item.section.program?.program_id ?? ''
const termOf = (item: FacultyAttendanceAssignment) => JSON.stringify([item.academic_year_id, item.semester_id])
const unique = <T,>(items: T[], key: (item: T) => string) => [...new Map(items.map((item) => [key(item), item])).values()]

/** All choices come from the role's authorized sections; batch is a saved cohort. */
export default function StudentRosterFilters({ token, assignments, selected, batchId, onBatch, onSection, onRefresh, refreshing, showBatch = true }: {
  token: string
  assignments: FacultyAttendanceAssignment[]
  selected: FacultyAttendanceAssignment
  batchId: string
  onBatch: (id: string) => void
  onSection: (id: string) => void
  onRefresh: () => void
  refreshing: boolean
  showBatch?: boolean
}) {
  const api = useStudentWorkspaceApi()
  const programId = branchOf(selected)
  const batches = useApiQuery([api.namespace, 'students', token, selected.section_id, 'roster-batches'],
    () => api.getBatches(token, selected.section_id, true), showBatch && !!programId)
  const courses = [...new Set(assignments.map(courseOf))].sort()
  const branches = unique(assignments.filter((item) => courseOf(item) === courseOf(selected)), branchOf)
  const inBranch = assignments.filter((item) => branchOf(item) === programId && courseOf(item) === courseOf(selected))
  const sections = unique(inBranch, (item) => item.section.code).sort((a, b) => a.section.code.localeCompare(b.section.code, undefined, { numeric: true }))
  const inSection = inBranch.filter((item) => item.section.code === selected.section.code)
  const terms = unique(inSection, termOf)
  const subjects = unique(inSection.filter((item) => termOf(item) === termOf(selected)), (item) => item.section_id)
  const options = batches.isError ? [] : (batches.data ?? []).filter((item) => item.program_id === programId)

  function choose(candidates: FacultyAttendanceAssignment[]) {
    // Preserve the current section, term and subject whenever the new branch offers them.
    const score = (item: FacultyAttendanceAssignment) =>
      Number(item.section.code === selected.section.code) * 4 + Number(termOf(item) === termOf(selected)) * 2
      + Number(item.section.course.code === selected.section.course.code)
    const next = [...candidates].sort((a, b) => score(b) - score(a))[0]
    if (next) {
      if (branchOf(next) !== programId) onBatch('')
      onSection(next.section_id)
    }
  }

  return <section className="students-academic-filters" aria-label="Roster filters">
    <div className="students-academic-filters-heading">
      <h2><SlidersHorizontal aria-hidden="true" />Filter students</h2>
      <button type="button" className="students-button" disabled={refreshing || batches.isFetching} onClick={() => { onRefresh(); if (showBatch && programId) void batches.refetch() }}><RefreshCw aria-hidden="true" />Refresh sections</button>
    </div>
    <div className="students-academic-filter-grid">
      <label className="students-filter-label">Course<select value={courseOf(selected)} onChange={(event) => choose(assignments.filter((item) => courseOf(item) === event.target.value))}>
        {courses.map((course) => <option key={course} value={course}>{course || 'Course unavailable'}</option>)}
      </select></label>
      <label className="students-filter-label">Branch<select value={programId} onChange={(event) => choose(assignments.filter((item) => branchOf(item) === event.target.value))}>
        {branches.map((item) => <option key={branchOf(item)} value={branchOf(item)}>{item.section.program?.name || 'Branch unavailable'}</option>)}
      </select></label>
      {showBatch && <label className="students-filter-label">Batch<select value={batchId} disabled={!programId || batches.isPending || batches.isError} onChange={(event) => onBatch(event.target.value)}>
        <option value="">{programId && batches.isPending ? 'Loading batches…' : 'All batches'}</option>
        {options.map((batch) => <option key={batch.batch_id} value={batch.batch_id}>{batch.start_year}–{batch.end_year}{!batch.is_active ? ' (archived)' : ''}</option>)}
      </select></label>}
      <label className="students-filter-label">Section<select value={selected.section.code} onChange={(event) => choose(inBranch.filter((item) => item.section.code === event.target.value))}>
        {sections.map((item) => <option key={item.section.code} value={item.section.code}>Section {item.section.code}</option>)}
      </select></label>
      <label className="students-filter-label">Semester<select value={termOf(selected)} onChange={(event) => choose(inSection.filter((item) => termOf(item) === event.target.value))}>
        {terms.map((item) => <option key={termOf(item)} value={termOf(item)}>{[item.section.semester?.name || 'Semester unavailable', item.section.academic_year?.name].filter(Boolean).join(' · ')}</option>)}
      </select></label>
      {subjects.length > 1 && <label className="students-filter-label">Subject<select value={selected.section_id} onChange={(event) => onSection(event.target.value)}>
        {subjects.map((item) => <option key={item.section_id} value={item.section_id}>{item.section.course.code} · {item.section.course.name}</option>)}
      </select></label>}
    </div>
    {showBatch && batches.isError && <div role="alert" className="students-filter-notice">{batches.error instanceof Error ? batches.error.message : 'Batches could not be loaded.'}<button type="button" className="students-text-button" onClick={() => void batches.refetch()}>Retry batches</button></div>}
    {showBatch && !batches.isError && !batches.isPending && !options.length && <p className="students-filter-notice">No batches are configured for this branch. Add them in Academic Setup → Batches.</p>}
  </section>
}
