import { useRef, useState } from 'react'
import { Mail } from 'lucide-react'
import { AdminApiError } from '../../services/admin/adminApi.ts'
import type { ClassStudentRegistration, StudentInvitationDelivery } from '../../services/students/studentRegistrationApi.ts'
import { useStudentWorkspaceApi } from './StudentWorkspaceContext.tsx'

const done = (status?: StudentInvitationDelivery['status']) => status === 'sent' || status === 'already_sent'

export default function StudentRegistrationInvitations({ token, sectionId, students, disabled = false, onDone, onBusyChange }: {
  token: string
  sectionId: string
  students: ClassStudentRegistration[]
  disabled?: boolean
  onDone?: () => void
  onBusyChange?: (busy: boolean) => void
}) {
  const api = useStudentWorkspaceApi()
  const [results, setResults] = useState<Record<string, StudentInvitationDelivery>>({})
  const [busy, setBusy] = useState(false)
  const [dismissedFor, setDismissedFor] = useState('')
  const registeredIds = students.map((student) => student.registration_id).sort().join(',')
  const sending = useRef(false)
  const resultOf = (student: ClassStudentRegistration) => results[student.registration_id] ?? student.invitation_delivery
  const remaining = students.filter((student) => !done(resultOf(student)?.status))
  const attempted = students.some((student) => resultOf(student))
  const failed = students.filter((student) => resultOf(student)?.status === 'failed').length
  const sent = students.filter((student) => done(resultOf(student)?.status)).length
  if (!students.length || dismissedFor === registeredIds) return null

  async function send() {
    if (sending.current || disabled) return
    sending.current = true
    setBusy(true)
    onBusyChange?.(true)
    try {
      let stop = ''
      for (const student of remaining) {
        let result: StudentInvitationDelivery
        try {
          if (stop) throw new Error(`Not attempted: ${stop}`)
          result = await api.sendInvitation(token, sectionId, student.registration_id)
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Invitation could not be sent. Try again.'
          result = { registration_id: student.registration_id, status: 'failed', message }
          if (error instanceof AdminApiError && [401, 403].includes(error.status)) stop = message
        }
        setResults((previous) => ({ ...previous, [student.registration_id]: result }))
      }
    } finally {
      sending.current = false
      setBusy(false)
      onBusyChange?.(false)
    }
  }

  return <section className="students-invitation-results" aria-label="Student invitation emails" aria-busy={busy}>
    <h3><Mail aria-hidden="true" />{attempted ? 'Invitation email results' : `Send registration invitations to ${students.length === 1 ? 'this student' : `all ${students.length} registered students`}?`}</h3>
    <p>Students will receive a link to complete account registration. Their accounts still require approval.</p>
    {attempted && <p role="status">Accepted for delivery: {sent} · Failed: {failed} · Remaining: {remaining.length - failed}</p>}
    {attempted && <ul>{students.map((student) => <li key={student.registration_id}><strong>{student.student_name}</strong><span>{student.email}</span><span>{resultOf(student)?.message ?? 'Not sent yet.'}</span></li>)}</ul>}
    <div className="students-invitation-actions">
      {!!remaining.length && <button type="button" className="students-button primary" disabled={busy || disabled} onClick={() => void send()}>{busy ? 'Sending invitation emails…' : attempted ? 'Retry unsent invitations' : students.length === 1 ? 'Send invitation email' : 'Send invitations to all'}</button>}
      <button type="button" className="students-button" disabled={busy || disabled} onClick={() => { if (onDone) onDone(); else setDismissedFor(registeredIds) }}>{attempted ? 'Done' : 'Not now'}</button>
    </div>
  </section>
}
