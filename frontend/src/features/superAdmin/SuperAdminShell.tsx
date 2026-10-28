import { useState } from 'react'
import { Building2, ScrollText, ShieldCheck, type LucideIcon } from 'lucide-react'
import WorkspaceFrame from '../workspace/WorkspaceFrame.tsx'
import WorkspacePageHeader from '../workspace/WorkspacePageHeader.tsx'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import { getPlatformIdentity } from '../../services/platform/platformApi.ts'
import { useAuth } from '../auth/session/AuthProvider.tsx'
import { hasPermission } from '../auth/access/permissions.ts'
import InstitutionManagement from './InstitutionManagement.tsx'
import PlatformAuditView from './PlatformAuditView.tsx'
import SuperAdminInvitations from './SuperAdminInvitations.tsx'

const PLATFORM_AREAS = [
  'University Admins',
  'Platform AI',
  'Usage',
  'Features',
  'Security',
  'Platform Settings',
] as const

type PlatformSection = 'institutions' | 'audit' | 'super-admins'
const icons: Record<PlatformSection, LucideIcon> = {
  institutions: Building2,
  audit: ScrollText,
  'super-admins': ShieldCheck,
}

/**
 * Phase 7.14 platform shell.
 *
 * The Phase 7.12 authorization gate is UNCHANGED and still runs first: the
 * shell renders only after `GET /platform/me` returns an allow response. Phase
 * 7.14 adds the read-only Platform Audit section; every other platform area
 * stays an honest "Coming Soon" placeholder with no fake functionality.
 *
 * Rendering the shell is a UX affordance, never an authorization decision —
 * each backend endpoint independently enforces `require_super_admin`.
 */
export default function SuperAdminShell() {
  const { user, accessToken, logout } = useAuth()
  const canReadPlatform = hasPermission(user?.effective_permissions, 'platform.read')
  const canReadAudit = hasPermission(user?.effective_permissions, 'platform.audit.read')
  const authorizationQuery = useApiQuery(
    ['platform', 'identity', accessToken],
    () => getPlatformIdentity(accessToken as string),
    accessToken !== null,
  )
  const authorization: 'checking' | 'allowed' | 'denied' =
    accessToken === null
      ? 'denied'
      : authorizationQuery.isPending
        ? 'checking'
        : authorizationQuery.isSuccess
          ? 'allowed'
          : 'denied'
  const [section, setSection] = useState<PlatformSection>(() => (canReadPlatform ? 'institutions' : 'audit'))

  if (authorization === 'checking') {
    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas px-6 text-content">
        <p>Verifying platform authorization…</p>
      </main>
    )
  }
  if (authorization === 'denied') {
    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas px-6 text-center text-content">
        <section className="max-w-lg rounded-xl border border-warning bg-warning-bg p-10">
          <h1 className="font-bold text-warning text-page">Platform access restricted</h1>
          <p className="mt-4 text-muted">Your current session is not authorized for platform administration.</p>
          <button
            type="button"
            onClick={logout}
            className="mt-6 rounded-lg bg-raised px-4 py-2 text-sm font-medium text-content"
          >
            Sign out
          </button>
        </section>
      </main>
    )
  }
  const navigation: { key: PlatformSection; label: string }[] = [
    ...(canReadPlatform
      ? [
          { key: 'institutions' as const, label: 'Institutions' },
          { key: 'super-admins' as const, label: 'Super Admins' },
        ]
      : []),
    ...(canReadAudit ? [{ key: 'audit' as const, label: 'Platform Audit' }] : []),
  ]
  return (
    <WorkspaceFrame<PlatformSection>
      navigation={navigation}
      currentView={section}
      icons={icons}
      onNavigate={setSection}
      panelLabel="Platform Administration"
      navigationLabel="Platform sections"
      identityLabel={user?.email ?? 'Platform administrator'}
      identityRole="Platform administrator"
      onLogout={logout}
      headerContent={<span className="admin-topbar-label">Platform-level workspace</span>}
      sidebarContent={
        <section className="workspace-upcoming" aria-label="Upcoming platform areas">
          <p>Coming soon</p>
          <ul>
            {PLATFORM_AREAS.map((area) => (
              <li key={area}>
                <span>{area}</span>
                <span>Soon</span>
              </li>
            ))}
          </ul>
        </section>
      }
    >
      {section === 'institutions' && canReadPlatform ? <InstitutionManagement /> : null}
      {section === 'audit' && canReadAudit ? <PlatformAuditView /> : null}
      {section === 'super-admins' && canReadPlatform ? (
        <>
          <WorkspacePageHeader
            title="Super Admins"
            eyebrow="Platform Administration"
            description="Invite and manage platform administrator access."
          />
          <SuperAdminInvitations />
        </>
      ) : null}
      {!canReadPlatform && !canReadAudit ? (
        <p role="status" className="text-sm text-muted">
          Your account has no platform sections available.
        </p>
      ) : null}
    </WorkspaceFrame>
  )
}
