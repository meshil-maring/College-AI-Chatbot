import { useState } from 'react'
import { RefreshCw } from 'lucide-react'
import AcademicPackagesWorkspace from '../../academic-packages/AcademicPackagesWorkspace.tsx'
import type { FacultyAttendanceAssignment } from '../../../services/faculty/facultyAttendanceApi.ts'
import { StudentsSearch } from '../StudentsUI.tsx'
import { useSubjectAssignment } from './useSubjectAssignment.ts'

export default function SubjectAssignment({
  token,
  assignment,
  batchId,
  packageAccess = false,
}: {
  token: string
  assignment: FacultyAttendanceAssignment
  batchId: string
  packageAccess?: boolean
}) {
  const [packagesOpen, setPackagesOpen] = useState(false)
  const { query, mutation, page, setPage, draftSearch, setDraftSearch, notice, search, searchStudents, assign } =
    useSubjectAssignment(token, assignment.section_id, batchId, assignment.can_manage ?? false)
  const subject = `${assignment.section.course.code} · ${assignment.section.course.name}`
  const busy = mutation.isPending || query.isFetching

  return (
    <section className="students-directory" aria-label="Subject Assignment">
      {packageAccess && (
        <div className="students-toolbar">
          <button
            type="button"
            className="students-button"
            aria-expanded={packagesOpen}
            onClick={() => setPackagesOpen(!packagesOpen)}
          >
            {packagesOpen ? 'Return to individual subject assignment' : 'Open complete package assignments'}
          </button>
        </div>
      )}
      {packageAccess && packagesOpen && <AcademicPackagesWorkspace accessToken={token} />}
      <div hidden={packageAccess && packagesOpen}>
        <div className="students-toolbar">
          <div className="students-toolbar-heading">
            <h2>Subject Assignment</h2>
            <p>Assign registered students to {subject}. Only students missing this subject are listed.</p>
          </div>
          <div className="students-table-actions">
            <StudentsSearch
              label="Search unassigned students"
              placeholder="Name or student number…"
              value={draftSearch}
              onChange={setDraftSearch}
              onSubmit={searchStudents}
            />
            <button type="button" className="students-button" disabled={busy} onClick={() => void query.refetch()}>
              <RefreshCw aria-hidden="true" />
              Refresh students
            </button>
          </div>
        </div>
        {!assignment.can_manage && (
          <p role="status" className="students-alert">
            You can view these students. Assigning subjects requires permission to manage this section.
          </p>
        )}
        {notice && (
          <p role="status" className="students-alert success">
            {notice}
          </p>
        )}
        {mutation.isError && (
          <p role="alert" className="students-alert error">
            {mutation.error instanceof Error ? mutation.error.message : 'Subject assignment failed. Try again.'}
          </p>
        )}
        {query.isError ? (
          <div role="alert" className="students-alert error">
            <span>
              {query.error instanceof Error ? query.error.message : 'Unassigned students could not be loaded.'}
            </span>
            <button type="button" className="students-button" onClick={() => void query.refetch()}>
              Retry students
            </button>
          </div>
        ) : query.isPending ? (
          <p role="status" className="students-empty">
            Loading unassigned students…
          </p>
        ) : !query.data?.items.length ? (
          <div role="status" className="students-empty">
            <h3>No unassigned students</h3>
            <p>
              {search
                ? 'No students match this search.'
                : 'No class registrations need this subject in the selected scope. Register students or choose another subject or batch.'}
            </p>
          </div>
        ) : (
          <>
            <div className="students-table-scroll">
              <table className="students-table directory">
                <caption className="sr-only">Students awaiting assignment to {subject}</caption>
                <thead>
                  <tr>
                    <th scope="col">Student</th>
                    <th scope="col">Register number</th>
                    <th scope="col">University roll</th>
                    <th scope="col">Batch</th>
                    <th scope="col">Subject assignment</th>
                  </tr>
                </thead>
                <tbody>
                  {query.data.items.map((student) => (
                    <tr key={student.registration_id}>
                      <td className="student-name">{student.student_name}</td>
                      <td>{student.register_number}</td>
                      <td>{student.university_roll_number ?? '—'}</td>
                      <td>
                        {student.batch_start_year}–{student.batch_end_year}
                      </td>
                      <td>
                        {student.assignment_errors.length > 0 && (
                          <p className="students-filter-notice">{student.assignment_errors.join(' ')}</p>
                        )}
                        <button
                          type="button"
                          className="students-button primary"
                          aria-label={`Assign ${student.student_name} to ${subject}`}
                          disabled={!assignment.can_manage || busy || student.assignment_errors.length > 0}
                          onClick={() => assign(student)}
                        >
                          {mutation.isPending && mutation.variables?.registration_id === student.registration_id
                            ? 'Assigning…'
                            : 'Assign subject'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="students-pagination">
              <p>{query.data.total} students awaiting this subject</p>
              <div>
                <button
                  type="button"
                  className="students-button"
                  disabled={page === 0 || busy}
                  onClick={() => setPage(page - 1)}
                >
                  Previous students
                </button>
                <span>Page {page + 1}</span>
                <button
                  type="button"
                  className="students-button"
                  disabled={(page + 1) * 25 >= query.data.total || busy}
                  onClick={() => setPage(page + 1)}
                >
                  Next students
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  )
}
