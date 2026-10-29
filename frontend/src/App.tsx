import { AuthGate, FacultyGate, RootGate, SuperAdminGate } from './app/RouteGates.tsx'
import { resolveAppRoute } from './app/routes.ts'
import AdminInvitationPage from './features/adminInvitation/AdminInvitationPage.tsx'
import { AuthProvider } from './features/auth/session/AuthProvider.tsx'
import ResetPasswordForm from './features/auth/password/ResetPasswordForm.tsx'
import UniversityRegistrationPage from './features/auth/registration/UniversityRegistrationPage.tsx'
import InstitutionEntryPage from './features/landing/InstitutionEntryPage.tsx'
import InstitutionGatewayPage from './features/landing/InstitutionGatewayPage.tsx'
import PublicChatPage, { PublicChatRouteError } from './features/publicChat/PublicChatPage.tsx'
import SuperAdminRegisterEntryPage from './features/superAdmin/SuperAdminRegisterEntryPage.tsx'
import SuperAdminRegistrationPage from './features/superAdmin/SuperAdminRegistrationPage.tsx'
import { useBrowserLocation } from './lib/navigation.ts'
function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-6 text-center text-content">
      <section className="max-w-lg rounded-xl border border-line bg-surface p-8 shadow-none">
        <h1 className="font-bold text-content text-page">Page not found</h1>
        <p className="mt-3 text-sm text-muted">This demo route is not available.</p>
        <a
          href="/"
          className="mt-6 inline-block rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-accent"
        >
          Return to College AI
        </a>
      </section>
    </main>
  )
}

function App() {
  const { pathname } = useBrowserLocation()
  const route = resolveAppRoute(pathname)
  if (route.kind === 'public-chat') {
    return route.institutionCode === null ? (
      <PublicChatRouteError />
    ) : (
      <PublicChatPage key={route.institutionCode} institutionCode={route.institutionCode} />
    )
  }
  if (route.kind === 'institution-ai')
    return <PublicChatPage key={route.institutionCode} institutionCode={route.institutionCode} />
  if (route.kind === 'institution-entry') return <InstitutionEntryPage />
  if (route.kind === 'institution') return <InstitutionGatewayPage institutionCode={route.institutionCode} />
  if (route.kind === 'not-found') return <NotFoundPage />
  if (route.kind === 'admin-invitation')
    return (
      <AuthProvider>
        <AdminInvitationPage token={route.token} />
      </AuthProvider>
    )
  if (route.kind === 'super-admin-register') return <SuperAdminRegisterEntryPage />
  if (route.kind === 'super-admin-invitation') {
    return <SuperAdminRegistrationPage token={route.token} />
  }
  // Public university onboarding. The reserved platform organization activates
  // the institution and its server-scoped University Admin immediately.
  if (route.kind === 'university-registration') return <UniversityRegistrationPage />
  if (route.kind === 'reset-password') {
    return <ResetPasswordForm onBackToLogin={() => window.location.assign('/login')} />
  }
  return (
    <AuthProvider>
      {route.kind === 'home' ? <RootGate /> : null}
      {route.kind === 'login' ? <AuthGate audience={route.audience} /> : null}
      {route.kind === 'super-admin' ? <SuperAdminGate /> : null}
      {route.kind === 'faculty' ? <FacultyGate /> : null}
    </AuthProvider>
  )
}

export default App

export { resolveAppRoute, resolvePublicInstitutionCode, type AppRoute } from './app/routes.ts'
