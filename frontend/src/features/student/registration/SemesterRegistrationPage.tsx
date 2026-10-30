import { useAuth } from '../../auth/session/AuthProvider.tsx'
import { hasPermission } from '../../auth/access/permissions.ts'
import { useSemesterRegistration } from './useSemesterRegistration.ts'
import SemesterRegistrationCard from './SemesterRegistrationCard.tsx'

export default function SemesterRegistrationPage() {
  const { accessToken, user, role, sessionGeneration } = useAuth()
  if (
    !accessToken ||
    !user?.institution_id ||
    role !== 'student' ||
    !hasPermission(user.effective_permissions, 'registration.own.read')
  )
    return <p role="status">Semester registration access is unavailable.</p>
  const identity = JSON.stringify([
    sessionGeneration ?? 0,
    user.user_id,
    user.institution_id,
    role,
    [...(user.effective_permissions ?? [])].sort(),
  ])
  return (
    <RegistrationSession
      key={identity}
      identity={identity}
      institutionId={user.institution_id}
      token={accessToken}
      canManage={hasPermission(user.effective_permissions, 'registration.own.manage')}
    />
  )
}

function RegistrationSession({
  identity,
  institutionId,
  token,
  canManage,
}: {
  identity: string
  institutionId: string
  token: string
  canManage: boolean
}) {
  const state = useSemesterRegistration(identity, institutionId, token)
  return (
    <section className="space-y-5" aria-label="Semester Registration">
      <p className="text-muted">
        Choose your complete subject option for the semester assigned by your institution. Common required subjects are
        included automatically.
      </p>
      {state.query.isPending && <p role="status">Loading semester registration…</p>}
      {state.error instanceof Error && (
        <div role="alert" className="ui-panel p-4">
          <p>{state.error.message}</p>
        </div>
      )}
      <button
        type="button"
        className="min-h-11 rounded-lg border border-control px-4 py-2 hover:bg-hover disabled:opacity-50"
        disabled={state.refreshing}
        onClick={() => void state.query.refetch()}
      >
        Refresh availability
      </button>
      {state.data && !state.data.items.length && (
        <p role="status">
          No semester has been assigned yet. Contact your institution administrator to assign your batch and section.
        </p>
      )}
      {state.data?.items.map((semester) => (
        <SemesterRegistrationCard
          key={semester.semester_registration_id}
          semester={semester}
          busy={state.busy}
          canManage={canManage}
          onComplete={state.complete}
        />
      ))}
    </section>
  )
}
