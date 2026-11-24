import StudentOnboardingProgress from './StudentOnboardingProgress.tsx'

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

/** Step progress for a registration card, with the uploaded file name during bulk import. */
export default function StudentOnboardingWorkflowHeader({
  mode,
  fileName = '',
  activeStep,
  onSelectStep,
}: {
  mode: 'single' | 'bulk'
  fileName?: string
  activeStep: number
  onSelectStep?: (index: number) => void
}) {
  return (
    <div className="student-onboarding-workflow-heading">
      <StudentOnboardingProgress steps={registrationSteps[mode]} activeStep={activeStep} onSelect={onSelectStep} />
      {mode === 'bulk' && fileName && <span className="student-onboarding-file-pill">{fileName}</span>}
    </div>
  )
}
