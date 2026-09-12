import { useCallback, useEffect, useState } from 'react'
import { AuthProvider, useAuth } from './features/auth/AuthProvider.tsx'
import LoginForm from './features/auth/LoginForm.tsx'
import ChangePasswordForm from './features/auth/ChangePasswordForm.tsx'
import ChatShell from './features/chat/ChatShell.tsx'
import AdminShell from './features/admin/AdminShell.tsx'
import AcademicsPanel from './features/academics/AcademicsPanel.tsx'
import { getAdminIdentity } from './services/adminApi.ts'
import { fetchDevAuthStatus } from './services/devAuth.ts'

/** DEVELOPMENT / TESTING ONLY — collapsible "Change Password" panel. */
function DevChangePasswordPanel() {
  const [devTestModeEnabled, setDevTestModeEnabled] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let cancelled = false
    void fetchDevAuthStatus().then((result) => {
      if (!cancelled) setDevTestModeEnabled(result.dev_test_mode)
    })
    return () => {
      cancelled = true
    }
  }, [])

  if (!devTestModeEnabled) return null

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {open ? (
        <div className="flex flex-col items-end gap-2">
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
          className="rounded-lg border border-amber-600/60 bg-slate-800 px-3 py-2 text-xs font-semibold text-amber-400 shadow-lg hover:bg-slate-700"
        >
          Change Password (Dev/Test only)
        </button>
      )}
    </div>
  )
}

function RestoringShell() {
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <main className="max-w-xl w-full text-center py-16">
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-10 shadow-xl">
          <h1 className="text-4xl font-bold text-white tracking-tight">College AI Chatbot</h1>
          <p className="mt-4 text-lg text-slate-300">Restoring your session…</p>
        </div>
      </main>
    </div>
  )
}

function StudentShell() {
  return (
    <>
      <ChatShell />
      <AcademicsPanel />
    </>
  )
}

function AuthenticatedShell() {
  const { accessToken } = useAuth()
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null)

  const checkAdmin = useCallback(async () => {
    if (accessToken === null) return
    try {
      await getAdminIdentity(accessToken)
      setIsAdmin(true)
    } catch {
      setIsAdmin(false)
    }
  }, [accessToken])

  useEffect(() => {
    void checkAdmin()
  }, [checkAdmin])

  if (isAdmin === null) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
        <main className="max-w-xl w-full text-center py-16">
          <div className="rounded-2xl border border-slate-700 bg-slate-800 p-10 shadow-xl">
            <h1 className="text-2xl font-bold text-white">Loading…</h1>
          </div>
        </main>
      </div>
    )
  }

  return isAdmin ? <AdminShell /> : <StudentShell />
}

function AuthGate() {
  const { status } = useAuth()
  if (status === 'restoring') {
    return <RestoringShell />
  }
  if (status === 'authenticated') {
    return (
      <>
        <AuthenticatedShell />
        <DevChangePasswordPanel />
      </>
    )
  }
  return <LoginForm />
}

function App() {
  return (
    <AuthProvider>
      <AuthGate />
    </AuthProvider>
  )
}

export default App
