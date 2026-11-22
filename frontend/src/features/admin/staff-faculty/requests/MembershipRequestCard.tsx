import { Check, RotateCw, X } from 'lucide-react'
import type { Department } from '../../../../types/academicSetup.ts'
import type { MembershipRequest, MembershipRole } from '../../../../types/admin.ts'
import {
  BUTTON_CLASS,
  DANGER_BUTTON_CLASS,
  formatDate,
  Initials,
  PRIMARY_BUTTON_CLASS,
  ROLE_OPTIONS,
  roleLabel,
  SELECT_CLASS,
  StatusBadge,
  Badge,
} from '../StaffFacultyUI.tsx'

interface Props {
  request: MembershipRequest
  departments: Department[]
  role: MembershipRole
  departmentId: string
  onRoleChange: (role: MembershipRole) => void
  onDepartmentChange: (departmentId: string) => void
  actionKey: string | null
  decide: (
    request: MembershipRequest,
    decision: 'approve' | 'reject',
    departmentId?: string,
    role?: MembershipRole,
  ) => Promise<void>
}

/** One sign-up request: who asked, for what, and the administrator's decision controls. */
export default function MembershipRequestCard({
  request,
  departments,
  role,
  departmentId,
  onRoleChange,
  onDepartmentChange,
  actionKey,
  decide,
}: Props) {
  const label = request.full_name || request.email
  const busy = actionKey !== null
  const requested = formatDate(request.created_at)
  const hintId = `request-hint-${request.request_id}`
  const changedRole = role !== request.requested_role

  return (
    <article className="flex flex-col gap-4 rounded-xl border border-line bg-canvas/40 p-4 lg:flex-row lg:items-end">
      <div className="flex min-w-0 flex-1 items-start gap-3 lg:min-w-64">
        <Initials name={label} />
        <div className="min-w-0 space-y-1">
          <p className="font-semibold text-content">{request.full_name || 'Unnamed applicant'}</p>
          <p className="break-all text-sm text-muted">{request.email}</p>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
            <StatusBadge status={request.status} />
            <Badge tone="info">Asked for {roleLabel(request.requested_role)}</Badge>
            {requested ? <span>Requested {requested}</span> : null}
          </div>
        </div>
      </div>

      {request.status === 'pending' ? (
        <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end lg:max-w-xl">
          <label className="flex flex-col gap-1 text-xs font-medium text-muted">
            Role
            <select
              aria-label={`Role for ${label}`}
              value={role}
              disabled={busy}
              onChange={(event) => onRoleChange(event.target.value as MembershipRole)}
              className={SELECT_CLASS}
            >
              {ROLE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-0 max-w-full flex-col gap-1 text-xs font-medium text-muted sm:flex-[1_1_14rem]">
            Department
            <select
              aria-label={`Department for ${label}`}
              aria-describedby={departmentId === '' ? hintId : undefined}
              value={departmentId}
              disabled={busy || departments.length === 0}
              onChange={(event) => onDepartmentChange(event.target.value)}
              className={`${SELECT_CLASS} w-full min-w-0`}
            >
              <option value="">Choose department…</option>
              {departments.map((department) => (
                <option key={department.department_id} value={department.department_id}>
                  {department.name} ({department.code})
                </option>
              ))}
            </select>
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={busy || departmentId === ''}
              onClick={() => void decide(request, 'approve', departmentId, role)}
              className={PRIMARY_BUTTON_CLASS}
            >
              <Check aria-hidden="true" className="size-4" />
              {actionKey === `approve:${request.request_id}` ? 'Approving…' : 'Approve'}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => void decide(request, 'reject')}
              className={DANGER_BUTTON_CLASS}
            >
              <X aria-hidden="true" className="size-4" />
              {actionKey === `reject:${request.request_id}` ? 'Rejecting…' : 'Reject'}
            </button>
          </div>
          {departmentId === '' || changedRole ? (
            <p id={hintId} className="basis-full text-xs text-muted">
              {departmentId === '' ? 'Choose a department to enable Approve.' : null}
              {changedRole ? ` Joins as ${roleLabel(role)} instead of the requested role.` : null}
            </p>
          ) : null}
        </div>
      ) : request.status === 'approved' ? (
        <div className="flex flex-col items-start gap-1 lg:items-end">
          <button
            type="button"
            disabled={busy}
            onClick={() => void decide(request, 'approve')}
            className={BUTTON_CLASS}
          >
            <RotateCw aria-hidden="true" className="size-4" />
            {actionKey === `approve:${request.request_id}` ? 'Retrying…' : 'Retry sign-in setup'}
          </button>
          <p className="text-xs text-muted">Use this only if the account cannot sign in.</p>
        </div>
      ) : null}
    </article>
  )
}
