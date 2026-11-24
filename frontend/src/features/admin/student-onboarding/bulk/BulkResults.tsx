import { Check, UsersRound } from 'lucide-react'
import type { StudentOnboardingBulkResult } from '../../../../types/admin/students.ts'
import StudentPageLink from '../shared/StudentPageLink.tsx'
import type { StudentImportRow } from './studentImport.ts'

export default function BulkResults({
  results,
  remaining,
  placementLabel,
  onFix,
  onStartOver,
}: {
  results: StudentOnboardingBulkResult[]
  remaining: StudentImportRow[]
  placementLabel: string
  onFix: () => void
  onStartOver: () => void
}) {
  const created = results.filter((item) => item.status === 'created').length
  const sent = results.filter((item) => item.delivery_status === 'sent').length
  const deliveryFailed = results.some((item) => item.delivery_status === 'failed')
  const needsAttention = remaining.length > 0 || deliveryFailed
  return (
    <div className="student-onboarding-results" role="region" aria-live="polite" aria-label="Bulk registration results">
      <span className={`student-onboarding-completion-icon ${needsAttention ? 'is-warning' : 'is-success'}`}>
        {needsAttention ? <UsersRound size={24} /> : <Check size={24} />}
      </span>
      <span className="student-onboarding-eyebrow">BULK REGISTRATION RESULTS</span>
      <h2>
        {remaining.length
          ? 'Some students still need attention'
          : deliveryFailed
            ? 'Some setup emails need to be resent'
            : 'Student invitations processed'}
      </h2>
      {placementLabel && (
        <p className="student-onboarding-result-placement">
          Placed in <strong>{placementLabel}</strong>
        </p>
      )}
      <div className="student-onboarding-result-counts">
        <span>
          <strong>{created}</strong>
          <small>Invitations created</small>
        </span>
        <span>
          <strong>{sent}</strong>
          <small>Setup emails sent</small>
        </span>
        <span>
          <strong>{remaining.length}</strong>
          <small>Rows to review</small>
        </span>
      </div>
      {results.length > 0 && (
        <ul className="student-onboarding-result-list">
          {results.map((item) => (
            <li
              key={item.row}
              className={item.status === 'created' && item.delivery_status === 'sent' ? 'is-created' : 'has-issues'}
            >
              <strong>Row {item.row}</strong>
              <span>
                {item.status === 'created'
                  ? item.delivery_status === 'sent'
                    ? 'Invitation sent'
                    : 'Email needs retry'
                  : item.status}
              </span>
              <small>{item.message}</small>
            </li>
          ))}
        </ul>
      )}
      {remaining.length > 0 && (
        <div className="student-onboarding-unresolved">
          <strong>Rows still in review</strong>
          {remaining.map((row) => (
            <p key={row.sourceRow}>
              Row {row.sourceRow}: {row.errors.join(' ') || 'Invitation could not be created.'}
            </p>
          ))}
        </div>
      )}
      <div className="student-onboarding-stage-actions">
        {remaining.length > 0 && (
          <button type="button" className="student-onboarding-secondary" onClick={onFix}>
            Fix remaining rows
          </button>
        )}
        <StudentPageLink page="all" className="student-onboarding-secondary student-onboarding-link-button">
          View in All Students
        </StudentPageLink>
        <StudentPageLink page="register" className="student-onboarding-secondary student-onboarding-link-button">
          Track setup invitations
        </StudentPageLink>
        <button type="button" className="student-onboarding-primary" onClick={onStartOver}>
          Start another upload
        </button>
      </div>
    </div>
  )
}
