import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { AcademicSection, AdmissionCohort } from '../../../../types/academicStructure.ts'
import type { StudentDirectoryRow, StudentDirectoryUpdateInput } from '../../../../types/admin/students.ts'
import { STUDENT_DIRECTORY_PAGE_SIZE } from './studentDirectoryQueries.ts'
import StudentRecordActions from './StudentRecordActions.tsx'
import './studentDirectoryTable.css'

export interface StudentDirectoryPermissions {
  canEdit: boolean
  canManagePlacement: boolean
  canDelete: boolean
  canResend: boolean
}

function statusLabel(row: StudentDirectoryRow): string {
  if (row.status === 'pending_sign_in') return 'Awaiting sign-in'
  if (row.status === 'signed_in') return 'Signed in'
  return 'No sign-in yet'
}

function formattedDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

function StudentRow({
  row,
  permissions,
  sections,
  cohorts,
  busyId,
  structureLoading,
  structureError,
  onEdit,
  onSetActive,
  onDelete,
  onCancelInvitation,
  onResend,
}: {
  row: StudentDirectoryRow
  permissions: StudentDirectoryPermissions
  sections: AcademicSection[]
  cohorts: AdmissionCohort[]
  busyId: string
  structureLoading: boolean
  structureError: string
  onEdit: (row: StudentDirectoryRow, input: StudentDirectoryUpdateInput) => Promise<boolean>
  onSetActive: (row: StudentDirectoryRow, active: boolean) => Promise<boolean>
  onDelete: (row: StudentDirectoryRow) => Promise<boolean>
  onCancelInvitation: (row: StudentDirectoryRow) => Promise<boolean>
  onResend: (row: StudentDirectoryRow) => void
}) {
  const linkExpired = row.expires_at ? new Date(row.expires_at).getTime() <= Date.now() : false
  const deliveryFailed = row.record_type === 'invitation' && row.email_delivery_status === 'failed'
  return (
    <tr>
      <td>
        <strong>{row.student_name}</strong>
        <span className="student-directory-secondary">{row.email || 'No email on file'}</span>
      </td>
      <td>
        <strong>{row.register_number || '—'}</strong>
        <span className="student-directory-secondary">{row.university_roll_number || 'No university roll no.'}</span>
      </td>
      <td>
        {row.course_name || 'Not assigned'}
        <span className="student-directory-secondary">{row.branch_name || 'Branch not assigned'}</span>
      </td>
      <td>
        {row.batch_name || '—'}
        <span className="student-directory-secondary">{row.section_name || 'Section not assigned'}</span>
      </td>
      <td>
        <span className={`student-directory-badge is-${row.status}`}>{statusLabel(row)}</span>
        {row.record_type === 'invitation' && (
          <span className="student-directory-secondary">
            {row.status === 'signed_in'
              ? 'Setup not completed'
              : linkExpired
                ? 'Setup link expired'
                : deliveryFailed
                  ? 'Email failed — link not delivered'
                  : `Email ${row.email_delivery_status || 'pending'}`}
          </span>
        )}
        {row.approval_status && <span className="student-directory-secondary">Approval: {row.approval_status}</span>}
      </td>
      <td>{row.last_sign_in_at ? formattedDate(row.last_sign_in_at) : '—'}</td>
      {permissions.canEdit || permissions.canDelete || permissions.canResend ? (
        <td>
          <StudentRecordActions
            student={row}
            canEdit={permissions.canEdit}
            canManagePlacement={permissions.canManagePlacement}
            canDelete={permissions.canDelete}
            canResend={permissions.canResend}
            sections={sections}
            cohorts={cohorts}
            onEdit={(input) => onEdit(row, input)}
            onSetActive={(active) => onSetActive(row, active)}
            onDelete={() => onDelete(row)}
            onCancelInvitation={() => onCancelInvitation(row)}
            onResend={() => onResend(row)}
            busy={busyId === row.record_id}
            structureLoading={structureLoading}
            structureError={structureError}
          />
        </td>
      ) : null}
    </tr>
  )
}

export default function StudentDirectoryTable({
  rows,
  total,
  offset,
  page,
  pages,
  setPage,
  permissions,
  sections,
  cohorts,
  busyId,
  structureLoading,
  structureError,
  onEdit,
  onSetActive,
  onDelete,
  onCancelInvitation,
  onResend,
}: {
  rows: StudentDirectoryRow[]
  total: number
  offset: number
  page: number
  pages: number
  setPage: (page: number) => void
  permissions: StudentDirectoryPermissions
  sections: AcademicSection[]
  cohorts: AdmissionCohort[]
  busyId: string
  structureLoading: boolean
  structureError: string
  onEdit: (row: StudentDirectoryRow, input: StudentDirectoryUpdateInput) => Promise<boolean>
  onSetActive: (row: StudentDirectoryRow, active: boolean) => Promise<boolean>
  onDelete: (row: StudentDirectoryRow) => Promise<boolean>
  onCancelInvitation: (row: StudentDirectoryRow) => Promise<boolean>
  onResend: (row: StudentDirectoryRow) => void
}) {
  const first = total ? offset + 1 : 0
  const last = Math.min(offset + STUDENT_DIRECTORY_PAGE_SIZE, total)
  const hasActions = permissions.canEdit || permissions.canDelete || permissions.canResend
  return (
    <>
      {rows.length ? (
        <div className="student-directory-table-scroll">
          <table className="student-directory-table">
            <thead>
              <tr>
                <th scope="col">Student</th>
                <th scope="col">Registration details</th>
                <th scope="col">Course / branch</th>
                <th scope="col">Batch / section</th>
                <th scope="col">Account status</th>
                <th scope="col">Last sign-in</th>
                {hasActions && <th scope="col">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <StudentRow
                  key={`${row.record_type}:${row.record_id}`}
                  row={row}
                  permissions={permissions}
                  sections={sections}
                  cohorts={cohorts}
                  busyId={busyId}
                  structureLoading={structureLoading}
                  structureError={structureError}
                  onEdit={onEdit}
                  onSetActive={onSetActive}
                  onDelete={onDelete}
                  onCancelInvitation={onCancelInvitation}
                  onResend={onResend}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="student-directory-empty" role="status">
          No students or pending invitations match these filters.
        </p>
      )}
      <div className="student-directory-pagination">
        <p role="status">
          Showing {first}–{last} of {total} records
        </p>
        <div aria-label="Student directory pagination">
          <button type="button" aria-label="Previous page" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            <ChevronLeft aria-hidden="true" />
          </button>
          <span>
            Page {page} of {pages}
          </span>
          <button type="button" aria-label="Next page" disabled={page >= pages} onClick={() => setPage(page + 1)}>
            <ChevronRight aria-hidden="true" />
          </button>
        </div>
      </div>
    </>
  )
}
