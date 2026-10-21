import { useAuth } from '../features/auth/session/AuthProvider.tsx'
import LoginForm, { type LoginAudience } from '../features/auth/login/LoginForm.tsx'
import LandingPage from '../features/landing/LandingPage.tsx'
import SuperAdminShell from '../features/superAdmin/SuperAdminShell.tsx'
import { AccountSecurityPanel } from './AccountSecurityPanel.tsx'
import { AuthenticatedExperience, UnsupportedRoleShell } from './AuthenticatedExperience.tsx'
import { StudentAccountSwitch } from './StudentAccountSwitch.tsx'
export function RestoringShell() {
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

export function AuthGate({ audience = 'general' }: { audience?: LoginAudience }) {
  const { status, role } = useAuth()
  if (status === 'restoring') {
    return <RestoringShell />
  }
  if (status === 'authenticated') {
    if (audience === 'student') {
      const registering = new URLSearchParams(window.location.search).get('register') === '1'
      if (role !== 'student' || registering) return <StudentAccountSwitch registering={registering} />
    }
    return (
      <>
        <AuthenticatedExperience />
      </>
    )
  }
  return <LoginForm audience={audience} />
}

export function RootGate() {
  const { status, error } = useAuth()
  if (status === 'restoring') return <RestoringShell />
  if (status === 'authenticated') {
    return (
      <>
        <AuthenticatedExperience />
      </>
    )
  }
  // A rejected/expired saved session still lands on the shared login form so
  // the established safe authentication error remains visible. Deliberate
  // sign-out (no error) returns to the public demo gateway.
  if (error !== null) return <LoginForm />
  return <LandingPage />
}

export function SuperAdminGate() {
  const { status, role, logout } = useAuth()
  if (status === 'restoring') return <RestoringShell />
  if (status !== 'authenticated') return <LoginForm audience="super_admin" />
  if (role === 'super_admin') {
    return (
      <>
        <SuperAdminShell />
        <AccountSecurityPanel />
      </>
    )
  }
  return <UnsupportedRoleShell onSignOut={logout} />
}

export function FacultyGate() {
  const { status, role, logout } = useAuth()
  if (status === 'restoring') return <RestoringShell />
  if (status !== 'authenticated') return <LoginForm audience="faculty" />
  if (role !== 'faculty')
    return (
      <UnsupportedRoleShell
        onSignOut={logout}
        message="This page requires a faculty account. Sign in with your faculty account to continue."
      />
    )
  return <AuthenticatedExperience />
}
