import { Hourglass } from 'lucide-react'
import StudentApprovalToolbar from './StudentApprovalToolbar.tsx'
import StudentApprovalTable from './StudentApprovalTable.tsx'
import { approvalErrorMessage, useStudentApprovalQueue, type ApprovalQueueOptions } from './useStudentApprovalQueue.ts'
import './students.css'

/** Administrator and staff account decisions use the same tenant-scoped contract. */
export default function StudentApprovalQueue(options: ApprovalQueueOptions) {
  const model = useStudentApprovalQueue(options)
  const { actionSuccess, actionError, queue, students, refresh } = model
  return (
    <section className="students-content students-scope" aria-label="Pending registrations">
      <StudentApprovalToolbar model={model} />
      <div aria-live="polite" className="students-queue-status">
        {actionSuccess && <p className="text-success">{actionSuccess}</p>}
        {actionError && (
          <p role="status" className="text-warning">
            {actionError}
          </p>
        )}
      </div>
      {queue.isPending ? (
        <p className="students-empty" role="status">
          Loading pending registrations…
        </p>
      ) : queue.isError ? (
        <div className="students-alert error" role="alert">
          <span>{approvalErrorMessage(queue.error)}</span>
          <button type="button" className="students-button" onClick={refresh}>
            Retry
          </button>
        </div>
      ) : !students.length ? (
        <div className="students-empty" role="status">
          <Hourglass aria-hidden="true" />
          <p>No students are awaiting approval right now.</p>
        </div>
      ) : (
        <StudentApprovalTable model={model} />
      )}
    </section>
  )
}
