import { Check, Mail, UserPlus } from 'lucide-react'
import { PlacementStep } from '../placement/PlacementStep.tsx'
import { usePlacementOptions } from '../placement/usePlacementOptions.ts'
import OnboardingPageHeading from '../shared/OnboardingPageHeading.tsx'
import StudentOnboardingWorkflowHeader, { registrationSteps } from '../shared/StudentOnboardingWorkflowHeader.tsx'
import StudentPageLink from '../shared/StudentPageLink.tsx'
import BulkResults from './BulkResults.tsx'
import StudentImportReview from './StudentImportReview.tsx'
import StudentImportUpload from './StudentImportUpload.tsx'
import { useBulkImport } from './useBulkImport.ts'

/** Students › Bulk Import: place a spreadsheet of students in one section and invite them. */
export default function BulkImportPage({ accessToken, identity }: { accessToken: string; identity: string }) {
  const bulk = useBulkImport(accessToken, identity)
  const placement = usePlacementOptions(accessToken, identity, true, bulk.sectionId)
  const { step, setStep, rows, readyRows, busy, error } = bulk

  return (
    <section className="student-onboarding-dashboard is-bulk-import" aria-label="Bulk student import">
      <OnboardingPageHeading
        trail={['Students', 'Bulk Import', registrationSteps.bulk[step].label]}
        title="Bulk Student Import"
        description="Upload a spreadsheet, fix any problems, then send setup links to every ready student."
        action={
          <StudentPageLink page="register" className="student-onboarding-secondary student-onboarding-link-button">
            <UserPlus size={17} aria-hidden="true" /> Add one student
          </StudentPageLink>
        }
      />
      <section className="student-onboarding-workflow" aria-label="Bulk student registration">
        <StudentOnboardingWorkflowHeader mode="bulk" fileName={bulk.fileName} activeStep={step} />
        {placement.error && (
          <p className="student-onboarding-inline-error" role="alert">
            {placement.error}
          </p>
        )}
        {step === 0 && (
          <PlacementStep
            placement={placement}
            sectionId={bulk.sectionId}
            plural
            onChange={bulk.setSectionId}
            continueLabel="Continue to upload"
            onContinue={() => setStep(1)}
          />
        )}
        {step === 1 && (
          <div className="student-onboarding-stage">
            <StudentImportUpload
              fileName={bulk.fileName}
              error={bulk.fileError}
              disabled={busy}
              onFile={(file) => void bulk.upload(file)}
            />
            <div className="student-onboarding-stage-actions">
              <button type="button" className="student-onboarding-secondary" onClick={() => setStep(0)}>
                Back to placement
              </button>
              <button
                type="button"
                className="student-onboarding-primary"
                disabled={!rows.length}
                onClick={() => setStep(2)}
              >
                Review student list <span aria-hidden="true">→</span>
              </button>
            </div>
          </div>
        )}
        {step === 2 && (
          <div className="student-onboarding-stage">
            <div className="student-onboarding-review-summary" aria-live="polite">
              <span>
                <strong>{rows.length}</strong> total students
              </span>
              <span className="is-ready">
                <Check size={16} /> {readyRows.length} ready
              </span>
              {bulk.issueRows > 0 && <span className="has-issues">{bulk.issueRows} need attention</span>}
            </div>
            <p className="student-onboarding-helper">
              Review the imported details below. Fix highlighted rows or remove them; only ready students will be
              invited.
            </p>
            <StudentImportReview rows={rows} disabled={busy} onEdit={bulk.editRow} onRemove={bulk.removeRow} />
            {error && (
              <p className="student-onboarding-inline-error" role="alert">
                {error}
              </p>
            )}
            <div className="student-onboarding-stage-actions">
              <button type="button" className="student-onboarding-secondary" disabled={busy} onClick={() => setStep(1)}>
                Back to upload
              </button>
              <button
                type="button"
                className="student-onboarding-primary"
                disabled={busy || !readyRows.length}
                onClick={() => void bulk.submit()}
              >
                <Mail size={17} />{' '}
                {busy
                  ? 'Sending setup links…'
                  : `Invite ${readyRows.length} ready student${readyRows.length === 1 ? '' : 's'}`}
              </button>
            </div>
          </div>
        )}
        {step === 3 && (
          <BulkResults results={bulk.results} remaining={rows} onFix={() => setStep(2)} onStartOver={bulk.reset} />
        )}
      </section>
    </section>
  )
}
