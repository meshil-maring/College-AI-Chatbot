import { useState } from 'react'
import { useAuth } from '../features/auth/session/AuthProvider.tsx'
import ChangePasswordForm from '../features/auth/password/ChangePasswordForm.tsx'

export function AccountSecurityPanel() {
  const [open, setOpen] = useState(false)
  const { logoutAll } = useAuth()

  return (
    <div className="fixed bottom-4 right-4 z-40 max-w-[calc(100vw-32px)]">
      {open ? (
        // A solid, height-capped card so the form stays readable and scrollable on short screens.
        <div
          id="account-security-panel"
          className="flex max-h-[calc(100dvh-32px)] w-[min(420px,calc(100vw-32px))] flex-col items-end gap-2 overflow-y-auto overscroll-contain rounded-xl border border-control bg-surface p-3 shadow-2xl"
        >
          <button
            type="button"
            onClick={() => void logoutAll()}
            className="w-full rounded-lg border border-control bg-surface px-3 py-2 text-left text-sm text-content hover:bg-hover"
          >
            Sign out all sessions
          </button>
          <ChangePasswordForm />
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="text-xs text-muted hover:text-content underline"
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
          className="rounded-lg border border-accent bg-surface px-3 py-2 text-sm font-semibold text-accent hover:bg-hover"
        >
          Account security
        </button>
      )}
    </div>
  )
}
