import { Check, ChevronLeft, ChevronRight, Hourglass, X } from 'lucide-react'
import { PAGE_SIZE, type ApprovalQueueModel } from './useStudentApprovalQueue.ts'
const field = (value: string | null) => value?.trim() || '—'

export default function StudentApprovalTable({ model }: { model: ApprovalQueueModel }) {
  const { visible, busyStudentId, canApprove, canReject, decide, filtered, currentPage, setPage } = model
  return (
    <>
      <div className="students-table-scroll">
        <table className="students-table directory students-approval-table">
          <caption className="sr-only">Student registrations awaiting approval</caption>
          <thead>
            <tr>
              <th scope="col">Student number</th>
              <th scope="col">Register number</th>
              <th scope="col">University roll number</th>
              <th scope="col">Email</th>
              <th scope="col">Enrollment status</th>
              <th scope="col">Approval status</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((student) => (
              <tr key={student.student_id}>
                <td className="student-name">{field(student.student_number)}</td>
                <td>{field(student.register_number)}</td>
                <td>{field(student.university_roll_number)}</td>
                <td>{field(student.email)}</td>
                <td>{field(student.status)}</td>
                <td>
                  <span className="students-status invalid">
                    <Hourglass aria-hidden="true" />
                    {field(student.approval_status)}
                  </span>
                </td>
                <td>
                  <div className="students-approval-actions">
                    {canApprove && (
                      <button
                        type="button"
                        className="students-button primary"
                        disabled={busyStudentId !== null}
                        onClick={() => void decide(student, 'approve')}
                      >
                        <Check aria-hidden="true" />
                        Approve
                      </button>
                    )}
                    {canReject && (
                      <button
                        type="button"
                        className="students-button"
                        disabled={busyStudentId !== null}
                        onClick={() => void decide(student, 'reject')}
                      >
                        <X aria-hidden="true" />
                        Reject
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {!visible.length && (
              <tr>
                <td colSpan={7} className="students-empty">
                  <p>No matching registrations.</p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="students-pagination">
        <p>
          Showing {filtered.length ? currentPage * PAGE_SIZE + 1 : 0}–
          {Math.min((currentPage + 1) * PAGE_SIZE, filtered.length)} of {filtered.length} registrations
        </p>
        <div>
          <button
            type="button"
            className="students-page"
            aria-label="Previous registration page"
            disabled={currentPage === 0 || busyStudentId !== null}
            onClick={() => setPage(currentPage - 1)}
          >
            <ChevronLeft aria-hidden="true" />
          </button>
          <span className="students-page active">{currentPage + 1}</span>
          <button
            type="button"
            className="students-page"
            aria-label="Next registration page"
            disabled={(currentPage + 1) * PAGE_SIZE >= filtered.length || busyStudentId !== null}
            onClick={() => setPage(currentPage + 1)}
          >
            <ChevronRight aria-hidden="true" />
          </button>
        </div>
      </div>
    </>
  )
}
