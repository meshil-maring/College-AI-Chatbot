import { useRef, useState } from 'react'
import { Check, ChevronLeft, ChevronRight, Hourglass, RefreshCw, X } from 'lucide-react'
import { useApiMutation, useApiQuery } from '../../hooks/useApiQuery.ts'
import { AdminApiError, approvePendingStudent, listPendingStudents, rejectPendingStudent } from '../../services/admin/adminApi.ts'
import type { PendingStudent } from '../../types/admin.ts'
import { StudentsSearch } from './StudentsUI.tsx'
import './students.css'
import { queryClient } from '../../lib/queryClient.ts'

function errorMessage(error: unknown) {
  return error instanceof AdminApiError && error.message ? error.message : 'The decision could not be saved. Please try again.'
}

const field = (value: string | null) => value?.trim() || '—'
const PAGE_SIZE = 25

/** Admin and staff share the same tenant-scoped approval contract and UI. */
export default function StudentApprovalQueue({ accessToken, namespace, canApprove = true, canReject = true }: {
  accessToken: string
  namespace: 'admin' | 'staff'
  canApprove?: boolean
  canReject?: boolean
}) {
  const [busyStudentId, setBusyStudentId] = useState<string | null>(null)
  const deciding = useRef(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())
  const [search, setSearch] = useState('')
  const [draftSearch, setDraftSearch] = useState('')
  const [page, setPage] = useState(0)
  const queue = useApiQuery([namespace, 'pending-students', accessToken], () => listPendingStudents(accessToken))
  const decision = useApiMutation<PendingStudent, { studentId: string; action: 'approve' | 'reject' }>({
    mutationFn: ({ studentId, action }) => action === 'approve' ? approvePendingStudent(accessToken, studentId) : rejectPendingStudent(accessToken, studentId),
  })
  const students = queue.isError ? [] : (queue.data ?? []).filter((student) => !dismissed.has(student.student_id))
  const term = search.trim().toLowerCase()
  const filtered = students.filter((student) => [student.student_number, student.register_number, student.university_roll_number, student.email].some((value) => value?.toLowerCase().includes(term)))
  const currentPage = Math.min(page, Math.max(0, Math.ceil(filtered.length / PAGE_SIZE) - 1))
  const visible = filtered.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE)

  function refresh() {
    setActionError(null)
    setActionSuccess(null)
    void queue.refetch()
  }

  async function decide(student: PendingStudent, action: 'approve' | 'reject') {
    if (deciding.current || (action === 'approve' ? !canApprove : !canReject)) return
    deciding.current = true
    setBusyStudentId(student.student_id)
    setActionError(null)
    setActionSuccess(null)
    try {
      await decision.mutateAsync({ studentId: student.student_id, action })
      setActionSuccess(action === 'approve'
        ? `Student ${student.student_number} approved. They can sign in after completing any required email verification.`
        : `Student ${student.student_number} rejected. Their account cannot sign in.`)
      setDismissed((current) => new Set(current).add(student.student_id))
      void queryClient.invalidateQueries({ queryKey: ['admin', 'students', accessToken] })
      void queryClient.invalidateQueries({ queryKey: ['admin', 'class-registrations', accessToken] })
      await queue.refetch()
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 409 && error.code === 'STUDENT_NOT_PENDING') {
        await queue.refetch()
        setDismissed(new Set())
        setActionError('This student was already processed. The queue has been refreshed.')
      } else setActionError(errorMessage(error))
    } finally {
      deciding.current = false
      setBusyStudentId(null)
    }
  }

  return <section className="students-content students-scope" aria-label="Pending registrations">
    <div className="students-toolbar">
      <div className="students-toolbar-heading"><h2>Pending registrations</h2><p>Student registrations awaiting a decision for your institution.</p></div>
      <div className="students-table-actions">
        <StudentsSearch value={draftSearch} onChange={setDraftSearch} onSubmit={() => { setSearch(draftSearch.trim()); setPage(0) }} label="Search pending registrations" placeholder="Student number, register number, roll number or email" />
        {search && <button type="button" className="students-button" onClick={() => { setSearch(''); setDraftSearch(''); setPage(0) }}>Clear filters</button>}
        <button type="button" className="students-button" onClick={refresh} disabled={queue.isFetching || busyStudentId !== null}><RefreshCw aria-hidden="true" />{queue.isFetching && !queue.isPending ? 'Refreshing…' : 'Refresh registrations'}</button>
      </div>
    </div>
    <div aria-live="polite" className="students-queue-status">
      {actionSuccess && <p className="text-emerald-300">{actionSuccess}</p>}
      {actionError && <p role="status" className="text-amber-300">{actionError}</p>}
    </div>
    {queue.isPending ? <p className="students-empty" role="status">Loading pending registrations…</p>
      : queue.isError ? <div className="students-alert error" role="alert"><span>{errorMessage(queue.error)}</span><button type="button" className="students-button" onClick={refresh}>Retry</button></div>
        : !students.length ? <div className="students-empty" role="status"><Hourglass aria-hidden="true" /><p>No students are awaiting approval right now.</p></div>
          : <>
            <div className="students-table-scroll"><table className="students-table directory students-approval-table">
              <caption className="sr-only">Student registrations awaiting approval</caption>
              <thead><tr><th scope="col">Student number</th><th scope="col">Register number</th><th scope="col">University roll number</th><th scope="col">Email</th><th scope="col">Enrollment status</th><th scope="col">Approval status</th><th scope="col">Actions</th></tr></thead>
              <tbody>{visible.map((student) => <tr key={student.student_id}>
                <td className="student-name">{field(student.student_number)}</td><td>{field(student.register_number)}</td><td>{field(student.university_roll_number)}</td><td>{field(student.email)}</td><td>{field(student.status)}</td>
                <td><span className="students-status invalid"><Hourglass aria-hidden="true" />{field(student.approval_status)}</span></td>
                <td><div className="students-approval-actions">
                  {canApprove && <button type="button" className="students-button primary" disabled={busyStudentId !== null} onClick={() => void decide(student, 'approve')}><Check aria-hidden="true" />Approve</button>}
                  {canReject && <button type="button" className="students-button" disabled={busyStudentId !== null} onClick={() => void decide(student, 'reject')}><X aria-hidden="true" />Reject</button>}
                </div></td>
              </tr>)}{!visible.length && <tr><td colSpan={7} className="students-empty"><p>No matching registrations.</p></td></tr>}</tbody>
            </table></div>
            <div className="students-pagination"><p>Showing {filtered.length ? currentPage * PAGE_SIZE + 1 : 0}–{Math.min((currentPage + 1) * PAGE_SIZE, filtered.length)} of {filtered.length} registrations</p><div>
              <button type="button" className="students-page" aria-label="Previous registration page" disabled={currentPage === 0 || busyStudentId !== null} onClick={() => setPage(currentPage - 1)}><ChevronLeft aria-hidden="true" /></button>
              <span className="students-page active">{currentPage + 1}</span>
              <button type="button" className="students-page" aria-label="Next registration page" disabled={(currentPage + 1) * PAGE_SIZE >= filtered.length || busyStudentId !== null} onClick={() => setPage(currentPage + 1)}><ChevronRight aria-hidden="true" /></button>
            </div></div>
          </>}
  </section>
}
