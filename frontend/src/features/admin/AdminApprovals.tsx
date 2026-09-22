/**
 * Phase 6.19 — Admin student-approval workspace.
 *
 * The Admin view of the SAME Phase 6.4 backend contract the staff shell uses
 * (`require_roles("admin", "staff")` with the tenant-pinned `_approval_scope`):
 *
 *   GET  /api/v1/admin/students/pending
 *   POST /api/v1/admin/students/{id}/approve
 *   POST /api/v1/admin/students/{id}/reject
 *
 * Server-side guarantees this UI relies on (never re-implemented here):
 *   - the queue is scoped to the caller's OWN institution by the backend
 *     (`_approval_scope`); this client never sends an institution_id;
 *   - approve/reject bodies accept NO fields, so no decision target can be
 *     spoofed from the client;
 *   - every decision is audit-logged server-side.
 *
 * Data minimization: each queue row renders ONLY the fields needed to make
 * the approval decision. Internal identifiers (student_id / user_id /
 * institution_id) are NEVER rendered.
 *
 * State discipline: loading / empty / error states with retry; approve and
 * reject actions surface a per-view status message (never color-only);
 * duplicate submissions are prevented by disabling both actions while one is
 * in flight; a 409 STUDENT_NOT_PENDING (another approver already decided)
 * triggers a queue refresh instead of a fake success.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AdminApiError,
  approvePendingStudent,
  listPendingStudents,
  rejectPendingStudent,
} from '../../services/adminApi.ts'
import type { PendingStudent } from '../../types/admin.ts'

type QueueState =
  | { phase: 'loading' }
  | { phase: 'ready'; students: PendingStudent[] }
  | { phase: 'error'; message: string }

const NEUTRAL_FIELD = '—'

function formatField(value: string | null): string {
  const trimmed = value?.trim()
  return trimmed ? trimmed : NEUTRAL_FIELD
}

function actionErrorMessage(error: unknown): string {
  if (error instanceof AdminApiError && error.message) return error.message
  return 'The decision could not be saved. Please try again.'
}

export default function AdminApprovals({ accessToken }: { accessToken: string }) {
  const [queue, setQueue] = useState<QueueState>({ phase: 'loading' })
  const [busyStudentId, setBusyStudentId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const requestGeneration = useRef(0)

  const loadQueue = useCallback(async () => {
    const generation = ++requestGeneration.current
    setActionError(null)
    setQueue({ phase: 'loading' })
    try {
      const students = await listPendingStudents(accessToken)
      // Discard a stale result (retry raced with a newer load).
      if (requestGeneration.current !== generation) return
      setQueue({ phase: 'ready', students })
    } catch (error) {
      if (requestGeneration.current !== generation) return
      setQueue({ phase: 'error', message: actionErrorMessage(error) })
    }
  }, [accessToken])

  useEffect(() => {
    void loadQueue()
  }, [loadQueue])

  async function decide(student: PendingStudent, decision: 'approve' | 'reject') {
    setBusyStudentId(student.student_id)
    setActionError(null)
    try {
      const updated =
        decision === 'approve'
          ? await approvePendingStudent(accessToken, student.student_id)
          : await rejectPendingStudent(accessToken, student.student_id)
      setQueue((prev) =>
        prev.phase === 'ready'
          ? {
              phase: 'ready',
              students: prev.students.filter((row) => row.student_id !== updated.student_id),
            }
          : prev,
      )
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 409) {
        // The student was already processed by another approver: refresh
        // the queue instead of pretending the local action succeeded.
        await loadQueue()
        setActionError('This student was already processed. The queue has been refreshed.')
      } else {
        setActionError(actionErrorMessage(error))
      }
    } finally {
      setBusyStudentId(null)
    }
  }

  if (queue.phase === 'loading') {
    return (
      <section
        aria-labelledby="admin-approvals-queue-heading"
        className="rounded-2xl border border-slate-700 bg-slate-800 p-6 shadow-lg"
      >
        <h2 id="admin-approvals-queue-heading" className="text-lg font-semibold text-white">
          Pending registrations
        </h2>
        <p role="status" className="mt-4 text-sm text-slate-300">
          Loading pending registrations…
        </p>
      </section>
    )
  }

  if (queue.phase === 'error') {
    return (
      <section
        aria-labelledby="admin-approvals-queue-heading"
        className="rounded-2xl border border-slate-700 bg-slate-800 p-6 shadow-lg"
      >
        <h2 id="admin-approvals-queue-heading" className="text-lg font-semibold text-white">
          Pending registrations
        </h2>
        <p role="alert" className="mt-4 text-sm text-amber-300">
          {queue.message}
        </p>
        <button
          type="button"
          onClick={() => void loadQueue()}
          className="mt-4 rounded-lg border border-slate-600 px-3 py-1.5 text-sm font-medium text-slate-200 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-400"
        >
          Retry
        </button>
      </section>
    )
  }
  const students = queue.students

  return (
    <section
      aria-labelledby="admin-approvals-queue-heading"
      className="rounded-2xl border border-slate-700 bg-slate-800 p-6 shadow-lg"
    >
      <h2 id="admin-approvals-queue-heading" className="text-lg font-semibold text-white">
        Pending registrations
      </h2>
      <p className="mt-1 text-sm text-slate-400">
        Student registrations awaiting a decision for your institution.
      </p>

      <div aria-live="polite" className="min-h-[1.5rem]">
        {actionError !== null ? (
          <p role="status" className="mt-3 text-sm text-amber-300">
            {actionError}
          </p>
        ) : null}
      </div>

      {students.length === 0 ? (
        <p role="status" className="mt-4 text-sm text-slate-300">
          No students are awaiting approval right now.
        </p>
      ) : (
        <ul className="mt-4 flex flex-col gap-4">
          {students.map((student) => (
            <li
              key={student.student_number}
              className="rounded-xl border border-slate-700 bg-slate-800/60 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <dl className="grid min-w-0 flex-1 gap-2 sm:grid-cols-2">
                  <div className="min-w-0">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">
                      Student number
                    </dt>
                    <dd className="mt-1 break-words text-sm text-slate-100">
                      {formatField(student.student_number)}
                    </dd>
                  </div>
                  <div className="min-w-0">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">
                      Email
                    </dt>
                    <dd className="mt-1 break-words text-sm text-slate-100">
                      {formatField(student.email)}
                    </dd>
                  </div>
                  <div className="min-w-0">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">
                      Register number
                    </dt>
                    <dd className="mt-1 break-words text-sm text-slate-100">
                      {formatField(student.register_number)}
                    </dd>
                  </div>
                  <div className="min-w-0">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">
                      University roll number
                    </dt>
                    <dd className="mt-1 break-words text-sm text-slate-100">
                      {formatField(student.university_roll_number)}
                    </dd>
                  </div>
                  <div className="min-w-0">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">
                      Enrollment status
                    </dt>
                    <dd className="mt-1 text-sm text-slate-100">{formatField(student.status)}</dd>
                  </div>
                  <div className="min-w-0">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">
                      Approval status
                    </dt>
                    <dd className="mt-1 text-sm text-slate-100">
                      {formatField(student.approval_status)}
                    </dd>
                  </div>
                </dl>
                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    disabled={busyStudentId !== null}
                    onClick={() => void decide(student, 'approve')}
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={busyStudentId !== null}
                    onClick={() => void decide(student, 'reject')}
                    className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                  >
                    Reject
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}