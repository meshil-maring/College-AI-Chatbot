import { Badge } from '../staff-faculty/StaffFacultyUI.tsx'

interface PermissionState {
  code: string
  inherited: boolean
  direct_grant_id: string | null
}

const ACTIONS: Record<string, string> = {
  read: 'View',
  view: 'View',
  write: 'Edit',
  update: 'Edit',
  manage: 'Manage',
  create: 'Create',
  delete: 'Delete',
  approve: 'Approve',
  publish: 'Publish',
}

/** "attendance.manage" → "Manage attendance"; the code is still shown beside it. */
export function permissionLabel(code: string) {
  const parts = code.split('.')
  const action = parts.length > 1 ? parts[parts.length - 1] : ''
  const resource = (parts.length > 1 ? parts.slice(0, -1) : parts).join(' ').replace(/[_-]+/g, ' ')
  const verb = ACTIONS[action] ?? (action ? action[0].toUpperCase() + action.slice(1) : '')
  return verb ? `${verb} ${resource}` : resource[0]?.toUpperCase() + resource.slice(1)
}

/**
 * Every permission this Staff member has or could be given, in one list.
 * Role grants are read-only. A delegable permission's box shows whether it is
 * granted; ticking or unticking it marks a change that Save applies.
 */
export default function StaffPermissionList({
  permissions,
  catalogue,
  changedCodes,
  onToggle,
  disabled,
}: {
  permissions: PermissionState[]
  catalogue: string[]
  changedCodes: ReadonlySet<string>
  onToggle: (code: string) => void
  disabled: boolean
}) {
  const byCode = new Map(permissions.map((item) => [item.code, item]))
  const codes = [...new Set([...permissions.map((item) => item.code), ...catalogue])].sort((a, b) =>
    permissionLabel(a).localeCompare(permissionLabel(b)),
  )
  const delegable = new Set(catalogue)

  if (codes.length === 0) {
    return <p className="text-sm text-muted">No permissions can be delegated in this institution.</p>
  }

  return (
    <fieldset disabled={disabled} className="min-w-0">
      <legend className="mb-2 text-sm font-medium text-content">Delegable permissions</legend>
      <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line">
        {codes.map((code) => {
          const state = byCode.get(code)
          const inherited = state?.inherited ?? false
          const granted = !inherited && Boolean(state?.direct_grant_id)
          const selectable = !inherited && delegable.has(code)
          const changed = selectable && changedCodes.has(code)
          const text = (
            <span className="flex min-w-0 flex-col">
              <span className="text-sm text-content">{permissionLabel(code)}</span>
              <span className="break-all font-mono text-xs text-muted">{code}</span>
            </span>
          )
          const badge = inherited ? (
            <Badge tone="neutral">Inherited role grant · read-only</Badge>
          ) : changed ? (
            <Badge tone={granted ? 'danger' : 'warning'}>{granted ? 'Will be revoked' : 'Will be granted'}</Badge>
          ) : granted ? (
            <Badge tone="success">{selectable ? 'Granted' : 'Direct grant'}</Badge>
          ) : (
            <Badge tone="neutral">Not granted</Badge>
          )
          return (
            <li key={code} className="flex flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2">
              {selectable ? (
                <label className="flex min-w-[10rem] flex-1 cursor-pointer items-center gap-3">
                  <input
                    type="checkbox"
                    className="size-5 shrink-0 accent-[var(--ui-accent)]"
                    checked={granted !== changed}
                    onChange={() => onToggle(code)}
                  />
                  {text}
                </label>
              ) : (
                <span className="flex min-w-[10rem] flex-1 items-center gap-3 pl-8">{text}</span>
              )}
              {badge}
            </li>
          )
        })}
      </ul>
    </fieldset>
  )
}
