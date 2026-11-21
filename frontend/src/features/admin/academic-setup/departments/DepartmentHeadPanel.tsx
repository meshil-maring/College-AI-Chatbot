import { useId, useState } from 'react'
import { useAuth } from '../../../auth/session/AuthProvider.tsx'
import type { Department } from '../../../../types/academicSetup.ts'
import { useDepartmentHead } from './useDepartmentHead.ts'

/** Appoint or remove the department's Head of Department, who decides transfers into it. */
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
  const { query, save, head, faculty } = useDepartmentHead(identity, institutionId, token, record.department_id)
  const [choice, setChoice] = useState<string | null>(null)
  const selected = choice ?? head?.faculty_user_id ?? ''
  const changed = selected !== (head?.faculty_user_id ?? '')
  const editable = canManage && record.is_active && !save.isPending
  return (
    <section aria-labelledby={`${id}-title`}>
      <h3 id={`${id}-title`}>Head of Department</h3>
      <p>The Head of Department approves or rejects student transfers into this department.</p>
      {query.isPending && <p role="status">Loading faculty…</p>}
      {query.error instanceof Error && <p role="alert">{query.error.message}</p>}
      {query.data && (
        <>
          <p>
            {head ? (
              <>
                Current: <strong>{head.name}</strong>
                {head.email ? ` (${head.email})` : ''}
                {!head.is_active_faculty && ' — no longer an active faculty member, so cannot review transfers'}
              </>
            ) : (
              'No Head of Department is appointed. Only administrators can decide transfers into this department.'
            )}
          </p>
          {!record.is_active && <p>Activate the department to appoint a Head of Department.</p>}
          <label htmlFor={`${id}-faculty`}>Faculty member</label>
          <select
            id={`${id}-faculty`}
            value={selected}
            disabled={!editable}
            onChange={(event) => setChoice(event.target.value)}
          >
            <option value="">No Head of Department</option>
            {faculty.map((member) => (
              <option key={member.user_id} value={member.user_id}>
                {member.name}
                {member.email && member.email !== member.name ? ` — ${member.email}` : ''}
              </option>
            ))}
          </select>
          {!faculty.length && <p>No active faculty members are available. Approve faculty accounts first.</p>}
          {save.error instanceof Error && <p role="alert">{save.error.message}</p>}
          <button
            type="button"
            className="academic-secondary-button"
            disabled={!editable || !changed}
            onClick={() => save.mutate(selected || null, { onSuccess: () => setChoice(null) })}
          >
            {save.isPending ? 'Saving…' : selected ? 'Save Head of Department' : 'Remove Head of Department'}
          </button>
        </>
      )}
    </section>
  )
}
