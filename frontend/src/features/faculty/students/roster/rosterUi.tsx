import { AlertCircle, AlertTriangle, ArrowLeft, CheckCircle2, Hourglass } from 'lucide-react'
import { useState } from 'react'
import { useApiQuery } from '../../../../hooks/useApiQuery.ts'
import { type FacultyAttendanceRosterRow } from '../../../../services/faculty/facultyAttendanceApi.ts'
import { useStudentWorkspaceApi } from '../../../students/StudentWorkspaceContext.tsx'
import { type FacultyStudentPage } from '../../workspace/facultyRoutes.ts'
export const panel = 'rounded-xl border border-[#26394e] bg-[#0d1c2c] p-5'

export const button =
  'rounded-lg border border-[#304862] px-3 py-2 text-sm text-slate-200 hover:bg-[#142638] focus:outline-none focus:ring-2 focus:ring-[#ffc72c] disabled:opacity-40'

export const PAGE_SIZE = 25

export type RosterStatus = FacultyAttendanceRosterRow['roster_status']

export const STATUS_LABELS: Record<RosterStatus, string> = {
  ACTIVE: 'Active',
  INACTIVE: 'Inactive',
  PENDING_APPROVAL: 'Pending approval',
  UNREGISTERED: 'Unregistered',
}

/** Row/pill tone per roster status — matches the admin students design palette. */
export const STATUS_TONE: Record<RosterStatus, string> = {
  ACTIVE: 'valid',
  PENDING_APPROVAL: 'invalid',
  UNREGISTERED: 'duplicate',
  INACTIVE: '',
}

export const ROSTER_STATUS_CARDS = [
  { status: 'ACTIVE', title: 'Active Students', description: 'Approved and active', Icon: CheckCircle2 },
  { status: 'PENDING_APPROVAL', title: 'Pending Approval', description: 'Awaiting account approval', Icon: Hourglass },
  {
    status: 'UNREGISTERED',
    title: 'Unregistered Students',
    description: 'No linked student account',
    Icon: AlertCircle,
  },
  { status: 'INACTIVE', title: 'Inactive Students', description: 'Registered but disabled', Icon: AlertTriangle },
] as const

export const STUDENT_PAGE_LABELS: Record<FacultyStudentPage, string> = {
  roster: 'Roster',
  history: 'Record history',
  'waiting-approval': 'Waiting approval',
  register: 'Register',
}

export function attendance(value: number | null | undefined) {
  return value == null ? 'No records' : `${value.toFixed(2)}%`
}

export function LoadError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <div role="alert" className="students-alert error">
      <AlertCircle aria-hidden="true" />
      <span>{error instanceof Error ? error.message : 'Student information could not be loaded.'}</span>
      <button type="button" className="students-button" onClick={onRetry}>
        Try again
      </button>
    </div>
  )
}

/** Server-side count of one roster status for the selected section (limit 1 — total only). */
export function useRosterStatusCount(
  token: string,
  sectionId: string,
  status: RosterStatus,
  enabled: boolean,
  batchId: string,
) {
  const api = useStudentWorkspaceApi()
  return useApiQuery(
    [api.namespace, 'students', token, sectionId, 'status-count', status, batchId],
    () =>
      api.getStudents(
        token,
        sectionId,
        new URLSearchParams({
          registration: status,
          limit: '1',
          offset: '0',
          ...(batchId ? { batch_id: batchId } : {}),
        }),
      ),
    enabled,
  )
}

export function StudentDetails({ token, rosterId, onClose }: { token: string; rosterId: string; onClose: () => void }) {
  const api = useStudentWorkspaceApi()
  const [page, setPage] = useState(0)
  const profileQuery = useApiQuery([api.namespace, 'students', token, rosterId, 'profile', page], () =>
    api.getProfile(token, rosterId, page * 50),
  )
  const profile = profileQuery.isError ? undefined : profileQuery.data

  return (
    <section className={`${panel} space-y-4`} aria-label="Student details">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-white">Student details</h2>
        <button type="button" className={`${button} flex items-center gap-2`} onClick={onClose}>
          <ArrowLeft aria-hidden="true" size={16} />
          Close details
        </button>
      </div>
      {profileQuery.isError ? (
        <LoadError
          error={profileQuery.error}
          onRetry={() => {
            void profileQuery.refetch()
          }}
        />
      ) : !profile ? (
        <p role="status" className="text-sm text-slate-400">
          Loading student details…
        </p>
      ) : (
        <>
          <h3 className="text-xl font-semibold text-white">{profile.student.student_name}</h3>
          <dl className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
            {[
              ['Register number', profile.student.register_number],
              ['University roll number', profile.student.university_roll_number ?? 'Not recorded'],
              ['Email', profile.student.email ?? 'Not recorded'],
              ['Registration status', STATUS_LABELS[profile.student.roster_status]],
              ['Section', profile.section.name],
              ['Subject attendance', attendance(profile.student.attendance_percentage)],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs text-slate-400">{label}</dt>
                <dd className="mt-1 break-words text-slate-100">{value}</dd>
              </div>
            ))}
          </dl>
          <div className="border-t border-[#26394e] pt-4">
            <h3 className="font-semibold text-white">Subject attendance history</h3>
            <p className="mt-1 text-xs text-slate-400">
              {profile.section.course.name} · {profile.total} recorded entries
            </p>
            {profile.history.length ? (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs text-slate-400">
                    <tr>
                      <th scope="col" className="py-2">
                        Date
                      </th>
                      <th scope="col">Attendance status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#26394e]">
                    {profile.history.map((record) => (
                      <tr key={record.record_id}>
                        <td className="py-3">{record.session_date}</td>
                        <td className="capitalize">{record.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="mt-4 text-sm text-slate-400">No attendance history for this subject.</p>
            )}
            <div className="mt-4 flex items-center justify-end gap-3">
              <button
                type="button"
                className={button}
                disabled={page === 0 || profileQuery.isFetching}
                onClick={() => setPage(page - 1)}
              >
                Previous records
              </button>
              <span className="text-xs text-slate-400">Page {page + 1}</span>
              <button
                type="button"
                className={button}
                disabled={(page + 1) * 50 >= profile.total || profileQuery.isFetching}
                onClick={() => setPage(page + 1)}
              >
                Next records
              </button>
            </div>
          </div>
        </>
      )}
    </section>
  )
}
