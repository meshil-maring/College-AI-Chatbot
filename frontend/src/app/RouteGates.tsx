import { useAuth } from '../features/auth/session/AuthProvider.tsx'
import LoginForm from '../features/auth/login/LoginForm.tsx'
import { loginPath } from '../features/auth/login/loginPaths.ts'
import LandingPage from '../features/landing/LandingPage.tsx'
import SuperAdminShell from '../features/superAdmin/SuperAdminShell.tsx'
import { AccountSecurityPanel } from './AccountSecurityPanel.tsx'
import { AuthenticatedExperience, UnsupportedRoleShell } from './AuthenticatedExperience.tsx'
import RegistrationForm from '../features/auth/registration/RegistrationForm.tsx'
import type { RegistrationType } from '../types/registration.ts'
import { AccountSwitch } from './AccountSwitch.tsx'
export function RestoringShell() {
  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center px-4">
      <main className="max-w-xl w-full text-center py-16">
        <div className="rounded-xl border border-line bg-surface p-10 shadow-none">
          <h1 className="font-bold text-content tracking-tight text-page">College AI Chatbot</h1>
          <p className="mt-4 text-lg text-muted">Restoring your session…</p>
        </div>
      </main>
    </div>
  )
}

/**
 * The one sign-in page for every account type. Once signed in, the server's
 * resolved role decides which workspace `/` opens.
 */
export function AuthGate() {
  const { status } = useAuth()
  if (status === 'restoring') {
    return <RestoringShell />
  }
  if (status === 'authenticated') {
    window.location.replace('/')
    return <RestoringShell />
  }
  return <LoginForm />
}

/**
 * Public registration for one account type (`/signup/student|faculty|staff`).
 * A signed-in visitor must choose to sign out first, so an existing session is
 * never mixed with a new registration. The type only selects the form; the
 * server decides the role and keeps the new account pending until approved.
 */
export function SignupGate({ registrationType }: { registrationType: RegistrationType }) {
  const { status } = useAuth()
  if (status === 'restoring') return <RestoringShell />
  if (status === 'authenticated') return <AccountSwitch audience={registrationType} />
  const institutionCode = new URLSearchParams(window.location.search).get('institution')
  return (
    <RegistrationForm
      registrationType={registrationType}
      onBackToLogin={() => window.location.assign(loginPath(institutionCode))}
    />
  )
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
  if (status !== 'authenticated') return <LoginForm />
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
  if (status !== 'authenticated') return <LoginForm />
  if (role !== 'faculty')
    return (
      <UnsupportedRoleShell
        onSignOut={logout}
        message="This page requires a faculty account. Sign in with your faculty account to continue."
      />
    )
  return <AuthenticatedExperience />
}
