import { useState } from 'react'
import { useAuth } from '../features/auth/session/AuthProvider.tsx'
import ChangePasswordForm from '../features/auth/password/ChangePasswordForm.tsx'

export function AccountSecurityPanel() {
  const [open, setOpen] = useState(false)
  const { logoutAll } = useAuth()

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {open ? (
        <div id="account-security-panel" className="flex flex-col items-end gap-2">
          <button
            type="button"
            onClick={() => void logoutAll()}
            className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-700"
          >
            Sign out all sessions
          </button>
          <ChangePasswordForm />
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="text-xs text-slate-400 hover:text-slate-200 underline"
          >
            Close
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-expanded={open}
          aria-controls="account-security-panel"
          className="rounded-lg border border-emerald-600/60 bg-slate-800 px-3 py-2 text-xs font-semibold text-emerald-400 shadow-lg hover:bg-slate-700"
        >
          Account security
        </button>
      )}
    </div>
  )
}
