import { useEffect, useRef } from 'react'
import { DANGER_BUTTON_CLASS, Initials, PRIMARY_BUTTON_CLASS, SELECT_CLASS } from '../staff-faculty/StaffFacultyUI.tsx'
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
    setSelectedUserId,
    state,
    catalogue,
    selectedCodes,
    setSelectedCodes,
    loading,
    busy,
    error,
    setError,
    notice,
    apply,
  } = useStaffPermissions(accessToken, focus)
  const headingRef = useRef<HTMLHeadingElement>(null)

  // Opened from the roster: move keyboard and screen-reader focus here too.
  useEffect(() => {
    if (focus !== null) headingRef.current?.focus({ preventScroll: true })
  }, [focus])

  const permissionByCode = new Map((state?.permissions ?? []).map((item) => [item.code, item]))
  const selected = members.find((member) => member.user_id === selectedUserId)
  const canRevoke =
    selectedCodes.length > 0 && selectedCodes.every((code) => permissionByCode.get(code)?.direct_grant_id)
  const canGrant = selectedCodes.length > 0

  return (
    <section
      aria-labelledby="staff-permission-heading"
      className="space-y-4 rounded-xl border border-line bg-surface p-4"
    >
      <div>
        <h2
          id="staff-permission-heading"
          ref={headingRef}
          tabIndex={-1}
          className="font-semibold text-content text-section focus:outline-none"
        >
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
      {notice ? (
        <p role="status" className="rounded-lg border border-success bg-success-bg p-3 text-sm text-success">
          {notice}
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
                onChange={(event) => {
                  setSelectedUserId(event.target.value)
                  setSelectedCodes([])
                  setError(null)
                }}
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
              selectedCodes={selectedCodes}
              setSelectedCodes={setSelectedCodes}
              disabled={busy || loading || state === null}
            />
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={busy || !canGrant}
                onClick={() => void apply('grant')}
                className={PRIMARY_BUTTON_CLASS}
              >
                Grant selected
              </button>
              <button
                type="button"
                disabled={busy || !canRevoke}
                onClick={() => void apply('revoke')}
                className={DANGER_BUTTON_CLASS}
              >
                Revoke selected direct grants
              </button>
              <p className="text-xs text-muted" aria-live="polite">
                {selectedCodes.length === 0
                  ? 'Select permissions to grant or revoke.'
                  : `${selectedCodes.length} selected${canRevoke ? '' : ' · Revoke needs every selected item to be granted'}`}
              </p>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
