import { Check, UserRound, UsersRound } from 'lucide-react'

export interface OnboardingStep {
  label: string
  description: string
}

export default function StudentOnboardingProgress({
  steps,
  activeStep,
}: {
  steps: OnboardingStep[]
  activeStep: number
}) {
  return (
    <ol
      className="student-onboarding-progress"
      aria-label="Registration steps"
      style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }}
    >
      {steps.map((step, index) => {
        const complete = index < activeStep
        const current = index === activeStep
        return (
          <li
            key={step.label}
            className={complete ? 'is-complete' : current ? 'is-current' : ''}
            aria-current={current ? 'step' : undefined}
          >
            <span className="student-onboarding-step-marker" aria-hidden="true">
              {complete ? <Check size={16} /> : index + 1}
            </span>
            <span className="student-onboarding-step-copy">
              <strong>{step.label}</strong>
              <small>{step.description}</small>
            </span>
          </li>
        )
      })}
    </ol>
  )
}

export function StudentRegistrationModePicker({
  mode,
  disabled,
  onChange,
}: {
  mode: 'single' | 'bulk'
  disabled: boolean
  onChange: (mode: 'single' | 'bulk') => void
}) {
  return (
    <div className="student-onboarding-mode-picker" role="group" aria-label="Choose registration method">
      <button
        type="button"
        disabled={disabled}
        className={mode === 'single' ? 'is-selected' : ''}
        aria-pressed={mode === 'single'}
        onClick={() => onChange('single')}
      >
        <span className="student-onboarding-mode-icon">
          <UserRound size={20} />
        </span>
        <span>
          <strong>One student</strong>
          <small>Enter details manually</small>
        </span>
        {mode === 'single' && <Check size={18} aria-hidden="true" />}
      </button>
      <button
        type="button"
        disabled={disabled}
        className={mode === 'bulk' ? 'is-selected' : ''}
        aria-pressed={mode === 'bulk'}
        onClick={() => onChange('bulk')}
      >
        <span className="student-onboarding-mode-icon">
          <UsersRound size={20} />
        </span>
        <span>
          <strong>Multiple students</strong>
          <small>Upload a CSV or Excel file</small>
        </span>
        {mode === 'bulk' && <Check size={18} aria-hidden="true" />}
      </button>
    </div>
  )
}
