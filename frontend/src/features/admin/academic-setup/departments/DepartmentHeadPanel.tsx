import { useId, useState } from 'react'
import { useAuth } from '../../../auth/session/AuthProvider.tsx'
import type { Department } from '../../../../types/academicSetup.ts'
import { useDepartmentHead } from './useDepartmentHead.ts'

/**
 * Appoint or remove the department's Heads of Department, who decide student
 * transfers into it. A department may have several equal heads.
 */
export default function DepartmentHeadPanel({ record, canManage }: { record: Department; canManage: boolean }) {
  const { accessToken, user, sessionGeneration } = useAuth()
  if (!accessToken || !user?.institution_id) return null
  const identity = JSON.stringify([sessionGeneration ?? 0, user.user_id, user.institution_id, 'admin'])
  return (
    <HeadSession
      key={`${identity}:${record.department_id}`}
      identity={identity}
      institutionId={user.institution_id}
      token={accessToken}
      record={record}
      canManage={canManage}
    />
  )
}

function HeadSession({
  identity,
  institutionId,
  token,
  record,
  canManage,
}: {
  identity: string
  institutionId: string
  token: string
  record: Department
  canManage: boolean
}) {
  const id = useId()
  const { query, add, end, heads, faculty } = useDepartmentHead(identity, institutionId, token, record.department_id)
  const [choice, setChoice] = useState('')
  const busy = add.isPending || end.isPending
  const current = new Set(heads.map((head) => head.faculty_user_id))
  const candidates = faculty.filter((member) => !current.has(member.user_id))
  const error = add.error ?? end.error
  return (
    <section aria-labelledby={`${id}-title`}>
      <h3 id={`${id}-title`}>Head of Department</h3>
      <p>
        Heads of Department approve or reject student transfers into this department. You can appoint more than one;
        each has the same authority and the first decision counts.
      </p>
      {query.isPending && <p role="status">Loading faculty…</p>}
      {query.error instanceof Error && <p role="alert">{query.error.message}</p>}
      {query.data && (
        <>
          {heads.length === 0 ? (
            <p>No Head of Department is appointed. Only administrators can decide transfers into this department.</p>
          ) : (
            <div aria-label="Current Heads of Department" role="group">
              {heads.map((head) => (
                <p key={head.faculty_user_id}>
                  <strong>{head.name}</strong>
                  {head.email && head.email !== head.name ? ` (${head.email})` : ''}
                  {!head.is_active_faculty && ' — no longer an active faculty member, so cannot review transfers'}{' '}
                  {canManage && (
                    <button
                      type="button"
                      className="academic-secondary-button"
                      disabled={busy}
                      aria-label={`Remove ${head.name} as Head of Department`}
                      onClick={() => end.mutate(head.faculty_user_id)}
                    >
                      {end.isPending && end.variables === head.faculty_user_id ? 'Removing…' : 'Remove'}
                    </button>
                  )}
                </p>
              ))}
            </div>
          )}
          {!record.is_active && <p>Activate the department to appoint a Head of Department.</p>}
          {canManage && record.is_active && (
            <>
              <label htmlFor={`${id}-faculty`}>Add a Head of Department</label>
              <select
                id={`${id}-faculty`}
                value={choice}
                disabled={busy || candidates.length === 0}
                onChange={(event) => setChoice(event.target.value)}
              >
                <option value="">Choose a faculty member…</option>
                {candidates.map((member) => (
                  <option key={member.user_id} value={member.user_id}>
                    {member.name}
                    {member.email && member.email !== member.name ? ` — ${member.email}` : ''}
                  </option>
                ))}
              </select>
              {!faculty.length && <p>No active faculty members are available. Approve faculty accounts first.</p>}
              <button
                type="button"
                className="academic-secondary-button"
                disabled={busy || choice === ''}
                onClick={() => add.mutate(choice, { onSuccess: () => setChoice('') })}
              >
                {add.isPending ? 'Adding…' : 'Add Head of Department'}
              </button>
            </>
          )}
          {error instanceof Error && <p role="alert">{error.message}</p>}
        </>
      )}
    </section>
  )
}
