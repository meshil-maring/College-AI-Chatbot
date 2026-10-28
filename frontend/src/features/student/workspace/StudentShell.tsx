/** Authenticated identity and institution information workspace. */

import { useState } from 'react'
import { Bell, BookOpen, Bot, UserCircle, type LucideIcon } from 'lucide-react'
import WorkspaceFrame from '../../workspace/WorkspaceFrame.tsx'
import WorkspacePageHeader from '../../workspace/WorkspacePageHeader.tsx'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import ChatShell from '../../chat/ChatShell.tsx'
import { STUDENT_VIEW_HEADINGS, buildStudentNavigation, type StudentView } from './studentNavigation.ts'
import { NoticesPage } from '../notices/NoticesPage.tsx'
import { ResourcesPage } from '../resources/ResourcesPage.tsx'
import { ProfilePage } from '../profile/ProfilePage.tsx'
import { getMyProfile } from '../../../services/students/studentApi.ts'
import { StudentAccessContext, useStudentResource, type StudentAccessDenial } from '../shared/useStudentResource.ts'
import { ErrorBlock, LoadingBlock } from '../shared/SectionState.tsx'

const icons: Record<StudentView, LucideIcon> = {
  profile: UserCircle,
  notices: Bell,
  resources: BookOpen,
  assistant: Bot,
}

export default function StudentShell() {
  const { user, role, logout } = useAuth()
  const [view, setView] = useState<StudentView>('profile')
  const [accessDenial, setAccessDenial] = useState<StudentAccessDenial | null>(null)
  // This endpoint exposes approval state even for pending students. This is a
  // UX boundary only; each data endpoint still enforces access server-side.
  const profile = useStudentResource(
    getMyProfile,
    'Unable to check your student account. Please try again.',
    '',
    'identity-profile',
  )
  const navigation = buildStudentNavigation(role, user?.effective_permissions)

  const displayName = user?.email?.trim() || 'Student'

  const approval = profile.data?.approval_status
  const inactive =
    profile.data?.status === 'inactive' ||
    profile.errorCode === 'STUDENT_INACTIVE' ||
    profile.errorCode === 'ACCOUNT_INACTIVE' ||
    accessDenial === 'STUDENT_INACTIVE' ||
    accessDenial === 'ACCOUNT_INACTIVE'
  if (profile.status !== 'loaded' || inactive || approval !== 'approved' || accessDenial !== null) {
    const loading = profile.status === 'loading' || profile.status === 'idle'
    const title = inactive
      ? 'Account inactive'
      : approval === 'pending'
        ? 'Approval pending'
        : approval === 'rejected'
          ? 'Registration not approved'
          : 'Student access unavailable'
    const guidance = inactive
      ? 'Your account is inactive. Contact your institution administrator for help with access.'
      : approval === 'pending'
        ? 'Your student registration is awaiting approval from your institution. You can access your profile after approval. Contact your institution administrator if you need help.'
        : approval === 'rejected'
          ? 'Your student registration was not approved. Contact your institution administrator to discuss your registration and next steps.'
          : accessDenial === 'STUDENT_NOT_APPROVED'
            ? 'Your account is not approved for student access. Contact your institution administrator for help with your approval status.'
            : 'Your student account access could not be confirmed. Contact your institution administrator for help.'
    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas px-4 text-content">
        <section
          aria-label="Student account access"
          className="w-full max-w-xl rounded-xl border border-line bg-surface p-8 shadow-none"
        >
          {loading ? (
            <LoadingBlock label="Checking your student account…" />
          ) : (
            <>
              <h1 className="font-bold text-content text-page">{title}</h1>
              {profile.status === 'error' && !inactive ? (
                <div className="mt-4">
                  <ErrorBlock
                    message={profile.error ?? 'Unable to check your student account.'}
                    onRetry={profile.reload}
                  />
                </div>
              ) : (
                <p role="status" className="mt-4 text-sm text-muted">
                  {guidance}
                </p>
              )}
              {profile.status === 'loaded' && accessDenial === null ? (
                <button
                  type="button"
                  onClick={profile.reload}
                  className="mt-6 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-ink hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent"
                >
                  Check status again
                </button>
              ) : null}
            </>
          )}
          <button
            type="button"
            onClick={logout}
            className="mt-6 ml-3 rounded-lg border border-control px-3 py-2 text-sm font-medium text-content hover:bg-hover focus:outline-none focus:ring-2 focus:ring-accent"
          >
            Sign out
          </button>
        </section>
      </main>
    )
  }

  return (
    <StudentAccessContext value={setAccessDenial}>
      <WorkspaceFrame<StudentView>
        navigation={navigation}
        currentView={view}
        icons={icons}
        onNavigate={setView}
        panelLabel="Student Portal"
        navigationLabel="Student navigation"
        identityLabel={displayName}
        identityRole="Student"
        onLogout={logout}
        onProfile={navigation.some((item) => item.key === 'profile') ? () => setView('profile') : undefined}
        onNotices={navigation.some((item) => item.key === 'notices') ? () => setView('notices') : undefined}
      >
        {navigation.some((item) => item.key === view) ? (
          <>
            {view !== 'assistant' && (
              <WorkspacePageHeader
                title={STUDENT_VIEW_HEADINGS[view]}
                description="Your student information and institution updates."
              />
            )}
            {view === 'notices' && <NoticesPage />}
            {view === 'resources' && <ResourcesPage />}
            {view === 'profile' && <ProfilePage profile={profile} />}
            {view === 'assistant' && (
              <section aria-label="AI Assistant">
                <ChatShell />
              </section>
            )}
          </>
        ) : (
          <section role="status" className="ui-panel text-center">
            <h1 className="text-page font-bold text-content">No available views</h1>
            <p className="mt-3 text-sm text-muted">Your account has no permissions for the selected student view.</p>
          </section>
        )}
      </WorkspaceFrame>
    </StudentAccessContext>
  )
}
