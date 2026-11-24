import { Check } from 'lucide-react'

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
