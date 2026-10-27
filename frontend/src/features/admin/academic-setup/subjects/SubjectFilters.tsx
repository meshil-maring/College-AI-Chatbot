import { Search, X } from 'lucide-react'
import type { SubjectsState } from './useSubjects.ts'
import { type SubjectSort, type SubjectStatus } from './subjectModel.ts'
import { COURSE_TYPE_LABELS as SUBJECT_TYPES } from '../forms/academicCourseTypes.ts'

export default function SubjectFilters({ state }: { state: SubjectsState }) {
  return (
    <div className="subject-filters" role="search" aria-label="Filter subjects">
      <label className="subject-search">
        <Search aria-hidden="true" />
        <span className="sr-only">Search subjects</span>
        <input
          type="search"
          value={state.search}
          placeholder="Search subjects by name or code..."
          onChange={(event) => state.setSearch(event.target.value)}
          disabled={!state.records}
        />
        {state.search && (
          <button type="button" aria-label="Clear subject search" onClick={() => state.setSearch('')}>
            <X aria-hidden="true" />
          </button>
        )}
      </label>
      <label>
        <span>Department</span>
        <select
          value={state.department}
          onChange={(event) => state.setDepartment(event.target.value)}
          disabled={!state.departments}
        >
          <option value="">All Departments</option>
          {state.departments?.map((item) => (
            <option key={item.department_id} value={item.department_id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Semester</span>
        <select
          value={state.semester}
          onChange={(event) => state.setSemester(event.target.value)}
          disabled={!state.assignments.semesters || !state.assignments.links}
        >
          <option value="">All Semesters</option>
          {state.assignments.semesters?.map((item) => (
            <option key={item.semester_id} value={item.semester_id}>
              {item.name} ({item.code})
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Subject Type</span>
        <select
          value={state.type}
          onChange={(event) => state.setType(event.target.value)}
          disabled={!state.assignments.links}
        >
          <option value="">All Types</option>
          {Object.entries(SUBJECT_TYPES).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Status</span>
        <select
          value={state.status}
          onChange={(event) => state.setStatus(event.target.value as SubjectStatus)}
          disabled={!state.records}
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </label>
      <label className="subject-mobile-sort">
        <span>Sort by</span>
        <select
          value={state.sort}
          onChange={(event) => state.setSort(event.target.value as SubjectSort)}
          disabled={!state.records}
        >
          <option value="code-asc">Code (A - Z)</option>
          <option value="code-desc">Code (Z - A)</option>
          <option value="name-asc">Name (A - Z)</option>
          <option value="name-desc">Name (Z - A)</option>
          <option value="is_active-asc">Inactive first</option>
          <option value="is_active-desc">Active first</option>
        </select>
      </label>
    </div>
  )
}
