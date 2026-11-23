import { useEffect, useRef } from 'react'
import { BUTTON_CLASS, Initials, PRIMARY_BUTTON_CLASS, SELECT_CLASS } from '../staff-faculty/StaffFacultyUI.tsx'
import StaffPermissionList from './StaffPermissionList.tsx'
import { useStaffPermissions, type StaffPermissionFocus } from './useStaffPermissions.ts'

export default function StaffPermissionManager({
  accessToken,
  focus = null,
}: {
  accessToken: string
  focus?: StaffPermissionFocus | null
}) {
  const {
    members,
    selectedUserId,
    selectMember,
    state,
    catalogue,
    changedCodes,
    toGrant,
    toRevoke,
    toggle,
    editing,
    startEditing,
    cancelEditing,
    loading,
    busy,
    error,
    save,
  } = useStaffPermissions(accessToken, focus)
  const headingRef = useRef<HTMLHeadingElement>(null)

  // Opened from the roster: move keyboard and screen-reader focus here too.
  useEffect(() => {
    if (focus !== null) headingRef.current?.focus({ preventScroll: true })
  }, [focus])

  const selected = members.find((member) => member.user_id === selectedUserId)
  const hasChanges = changedCodes.size > 0
  const summary = [
    toGrant.length ? `${toGrant.length} to grant` : '',
    toRevoke.length ? `${toRevoke.length} to revoke` : '',
  ]
    .filter(Boolean)
    .join(' · ')

  return (
    <section
      aria-labelledby="staff-permission-heading"
      className="space-y-4 rounded-xl border border-line bg-surface p-4"
    >
      <div>
        <h2 id="staff-permission-heading" ref={headingRef} tabIndex={-1} className="sr-only">
          Staff permissions
        </h2>
        <p className="mt-1 max-w-[70ch] text-sm text-muted">
          Give an active Staff member extra duties in your institution. Permissions that come with their role are shown
          for reference and cannot be changed here.
        </p>
      </div>
      {error ? (
        <p role="alert" className="rounded-lg border border-danger bg-danger-bg p-3 text-sm text-danger">
          {error}
        </p>
      ) : null}
      {loading ? (
        <p role="status" className="text-sm text-muted">
          Loading Staff permission data…
        </p>
      ) : members.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted">
          No active Staff members are available in this institution.
        </p>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[minmax(240px,320px)_1fr]">
          <div className="space-y-3">
            <label className="flex flex-col gap-1 text-sm font-medium text-content">
              Staff member
              <select
                className={`${SELECT_CLASS} w-full`}
                value={selectedUserId}
                disabled={busy || loading}
                onChange={(event) => selectMember(event.target.value)}
              >
                {members.map((member) => (
                  <option key={member.user_id} value={member.user_id}>
                    {member.name || member.email} ({member.email})
                  </option>
                ))}
              </select>
            </label>
            {selected ? (
              <div className="flex items-center gap-3 rounded-lg border border-line p-3">
                <Initials name={selected.name || selected.email} />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-content">{selected.name || 'Pending setup'}</p>
                  <p className="break-all text-xs text-muted">{selected.email}</p>
                </div>
              </div>
            ) : null}
          </div>
          <div className="min-w-0 space-y-3">
            <StaffPermissionList
              permissions={state?.permissions ?? []}
              catalogue={catalogue}
              changedCodes={changedCodes}
              onToggle={toggle}
              disabled={!editing || busy || loading || state === null}
            />
            {editing ? (
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  disabled={busy || !hasChanges}
                  onClick={() => void save()}
                  className={PRIMARY_BUTTON_CLASS}
                >
                  Save changes
                </button>
                <button type="button" disabled={busy} onClick={cancelEditing} className={BUTTON_CLASS}>
                  Cancel
                </button>
                <p className="text-xs text-muted" aria-live="polite">
                  {hasChanges ? summary : 'Tick a permission to grant it, or untick it to revoke it.'}
                </p>
              </div>
            ) : (
              <button
                type="button"
                disabled={busy || loading || state === null}
                onClick={startEditing}
                className={PRIMARY_BUTTON_CLASS}
              >
                Edit permissions
              </button>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
