import { useEffect, useRef, useState } from 'react'
import {
  changeStaffPermissions,
  getDelegableStaffPermissions,
  getStaffPermissions,
  listMembershipRoster,
  type StaffPermissionState,
} from '../../services/adminApi.ts'

export default function StaffPermissionManager({ accessToken }: { accessToken: string }) {
  const [members, setMembers] = useState<Array<{ user_id: string; name: string; email: string }>>([])
  const [selectedUserId, setSelectedUserId] = useState('')
  const [state, setState] = useState<StaffPermissionState | null>(null)
  const [catalogue, setCatalogue] = useState<string[]>([])
  const [selectedCodes, setSelectedCodes] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const selectedRequest = useRef(0)

  async function refreshSelected(userId: string) {
    const requestId = ++selectedRequest.current
    setError(null)
    setState(null)
    if (!userId) {
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const result = await getStaffPermissions(accessToken, userId)
      if (requestId === selectedRequest.current) setState(result)
    } finally {
      if (requestId === selectedRequest.current) setLoading(false)
    }
  }

  useEffect(() => {
    let current = true
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [roster, permissions] = await Promise.all([
          listMembershipRoster(accessToken, 'staff', 'active'),
          getDelegableStaffPermissions(accessToken),
        ])
        if (!current) return
        const activeMembers = roster.members.flatMap((member) =>
          member.user_id === null ? [] : [{
            user_id: member.user_id,
            name: member.name,
            email: member.email,
          }],
        )
        setMembers(activeMembers)
        setCatalogue(permissions)
        setSelectedUserId(activeMembers[0]?.user_id ?? '')
        if (activeMembers[0]) {
          const selectedState = await getStaffPermissions(accessToken, activeMembers[0].user_id)
          if (!current) return
          setState(selectedState)
        }
      } catch (cause) {
        if (current) setError(cause instanceof Error ? cause.message : 'Could not load Staff permissions.')
      } finally {
        if (current) setLoading(false)
      }
    }
    void load()
    return () => { current = false }
  }, [accessToken])

  async function apply(action: 'grant' | 'revoke') {
    if (!selectedUserId || selectedCodes.length === 0) return
    const verb = action === 'grant' ? 'Grant' : 'Revoke'
    if (!window.confirm(`${verb} ${selectedCodes.length} permission(s) for this Staff member?`)) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const result = await changeStaffPermissions(accessToken, selectedUserId, selectedCodes, action)
      setState(result.permissions)
      setSelectedCodes([])
      setNotice(`${verb} completed. ${result.changed} permission grant(s) changed.`)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : `Could not ${verb.toLowerCase()} permissions.`)
    } finally {
      setBusy(false)
    }
  }

  const permissionByCode = new Map((state?.permissions ?? []).map((item) => [item.code, item]))
  const selectable = catalogue.filter((code) => !permissionByCode.get(code)?.inherited)

  return (
    <section aria-labelledby="staff-permission-heading" className="space-y-4 rounded-2xl border border-slate-700 bg-slate-800 p-4">
      <h2 id="staff-permission-heading" className="text-lg font-semibold text-white">Scoped Staff permissions</h2>
      <p className="text-sm text-slate-300">
        Direct grants apply only to this active Staff account in your institution. Inherited role grants are read-only.
      </p>
      {error ? <p role="alert" className="rounded-lg border border-red-700 p-3 text-sm text-red-200">{error}</p> : null}
      {notice ? <p role="status" className="rounded-lg border border-emerald-700 p-3 text-sm text-emerald-200">{notice}</p> : null}
      {loading ? <p role="status">Loading Staff permission data…</p> : members.length === 0 ? (
        <p>No active Staff members are available in this institution.</p>
      ) : (
        <>
          <label className="block text-sm text-slate-200">
            Staff member
            <select
              className="mt-1 block w-full rounded-lg border border-slate-600 bg-slate-900 p-2"
              value={selectedUserId}
              disabled={busy || loading}
              onChange={(event) => {
                const userId = event.target.value
                setSelectedUserId(userId)
                setSelectedCodes([])
                setError(null)
                void refreshSelected(userId).catch((cause: unknown) =>
                  setError(cause instanceof Error ? cause.message : 'Could not load this Staff member.'),
                )
              }}
            >
              {members.map((member) => (
                <option key={member.user_id} value={member.user_id}>{member.name || member.email} ({member.email})</option>
              ))}
            </select>
          </label>
          <ul className="space-y-2">
            {state?.permissions.map((permission) => (
              <li key={permission.code} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-mono text-slate-100">{permission.code}</span>
                {permission.inherited ? <span className="text-slate-400">Inherited role grant · read-only</span> : null}
                {!permission.inherited && permission.direct_grant_id ? <span className="text-emerald-300">Direct grant</span> : null}
              </li>
            ))}
          </ul>
          <fieldset disabled={busy || loading || state === null} className="space-y-2">
            <legend className="text-sm font-medium text-slate-200">Delegable permissions</legend>
            {selectable.map((code) => (
              <label key={code} className="flex items-center gap-2 text-sm text-slate-200">
                <input
                  type="checkbox"
                  checked={selectedCodes.includes(code)}
                  onChange={(event) => setSelectedCodes((previous) =>
                    event.target.checked ? [...previous, code] : previous.filter((item) => item !== code),
                  )}
                  disabled={busy}
                />
                <span className="font-mono">{code}</span>
                {permissionByCode.get(code)?.direct_grant_id ? <span className="text-emerald-300">currently granted</span> : null}
              </label>
            ))}
          </fieldset>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={busy || selectedCodes.length === 0} onClick={() => void apply('grant')} className="rounded-lg bg-emerald-700 px-3 py-2 text-sm disabled:opacity-50">Grant selected</button>
            <button
              type="button"
              disabled={busy || selectedCodes.length === 0 || selectedCodes.some((code) => !permissionByCode.get(code)?.direct_grant_id)}
              onClick={() => void apply('revoke')}
              className="rounded-lg border border-red-700 px-3 py-2 text-sm text-red-200 disabled:opacity-50"
            >
              Revoke selected direct grants
            </button>
          </div>
        </>
      )}
    </section>
  )
}
