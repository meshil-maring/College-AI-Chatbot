import { useState } from 'react'
import type { StudentInvitation } from '../../../../types/admin/students.ts'
import type { PlacementOptions } from '../placement/usePlacementOptions.ts'
import { STATE_LABELS, invitationState } from './invitationFilters.ts'

/** One pending invitation, with resend and an inline section change limited to active sections. */
export default function InvitationRow({
  invite,
  placement,
  busy,
  onResend,
  onReassign,
}: {
  invite: StudentInvitation
  placement: Pick<PlacementOptions, 'cohorts' | 'sections'>
  busy: boolean
  onResend: (invitationId: string) => void
  onReassign: (invitationId: string, sectionId: string) => Promise<boolean>
}) {
  const [editing, setEditing] = useState(false)
  const [target, setTarget] = useState('')
  const state = invitationState(invite)
  const otherSections = placement.sections.filter(
    (section) => section.academic_section_id !== invite.academic_section_id,
  )
  const batches = placement.cohorts.filter((cohort) =>
    otherSections.some((section) => section.admission_cohort_id === cohort.admission_cohort_id),
  )

  return (
    <tr>
      <td>
        <strong>{invite.student_name}</strong>
        <small>{invite.email}</small>
      </td>
      <td>{invite.register_number}</td>
      <td>
        {editing ? (
          <div className="student-invitation-section-edit">
            <select
              aria-label={`New section for ${invite.student_name}`}
              value={target}
              disabled={busy}
              onChange={(event) => setTarget(event.target.value)}
            >
              <option value="">Choose a section</option>
              {batches.map((cohort) => (
                <optgroup key={cohort.admission_cohort_id} label={`${cohort.code} · ${cohort.name}`}>
                  {otherSections
                    .filter((section) => section.admission_cohort_id === cohort.admission_cohort_id)
                    .map((section) => (
                      <option key={section.academic_section_id} value={section.academic_section_id}>
                        {section.code} · {section.name}
                      </option>
                    ))}
                </optgroup>
              ))}
            </select>
            <div>
              <button
                type="button"
                className="is-primary"
                disabled={busy || !target}
                onClick={() =>
                  void onReassign(invite.invitation_id, target).then((saved) => {
                    if (saved) setEditing(false)
                  })
                }
              >
                Save
              </button>
              <button type="button" disabled={busy} onClick={() => setEditing(false)}>
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <>
            <strong>{invite.batch_code ?? invite.batch_name ?? '—'}</strong>
            <small>{[invite.section_code, invite.section_name].filter(Boolean).join(' · ') || '—'}</small>
          </>
        )}
      </td>
      <td>
        <span className={`student-invitation-status is-${state}`}>{STATE_LABELS[state]}</span>
      </td>
      <td>
        <time dateTime={invite.expires_at}>{new Date(invite.expires_at).toLocaleDateString()}</time>
      </td>
      <td>
        {!editing && (
          <div className="student-invitation-actions">
            <button
              type="button"
              disabled={busy}
              aria-label={`${state === 'expired' ? 'Send new link' : 'Resend link'} to ${invite.student_name}`}
              onClick={() => onResend(invite.invitation_id)}
            >
              {state === 'expired' ? 'Send new link' : 'Resend link'}
            </button>
            <button
              type="button"
              disabled={busy || !otherSections.length}
              aria-label={`Change section for ${invite.student_name}`}
              title={otherSections.length ? undefined : 'No other active section is available.'}
              onClick={() => {
                setTarget('')
                setEditing(true)
              }}
            >
              Change section
            </button>
          </div>
        )}
      </td>
    </tr>
  )
}
