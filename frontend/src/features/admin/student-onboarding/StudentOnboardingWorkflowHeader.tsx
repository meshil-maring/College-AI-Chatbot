import StudentOnboardingProgress, { type OnboardingStep } from './StudentOnboardingProgress.tsx'

export const registrationSteps = {
  single: [
    { label: 'Placement', description: 'Choose batch and section' },
    { label: 'Student details', description: 'Enter official information' },
    { label: 'Review & send', description: 'Check before inviting' },
  ],
  bulk: [
    { label: 'Placement', description: 'Choose batch and section' },
    { label: 'Upload File', description: 'Select your spreadsheet' },
    { label: 'Validate & Preview', description: 'Check and fix records' },
    { label: 'Import Result', description: 'View invitation status' },
  ],
}

export default function StudentOnboardingWorkflowHeader({
  mode,
  fileName,
  steps,
  activeStep,
}: {
  mode: 'single' | 'bulk'
  fileName: string
  steps: OnboardingStep[]
  activeStep: number
}) {
  return (
    <>
      <div className="student-onboarding-workflow-heading">
        <div>
          <span className="student-onboarding-eyebrow">
            {mode === 'single' ? 'INDIVIDUAL REGISTRATION' : 'BULK REGISTRATION'}
          </span>
          <h3>{mode === 'single' ? 'Add one student' : 'Add multiple students'}</h3>
        </div>
        {mode === 'bulk' && fileName && <span className="student-onboarding-file-pill">{fileName}</span>}
      </div>
      <StudentOnboardingProgress steps={steps} activeStep={activeStep} />
    </>
  )
}
