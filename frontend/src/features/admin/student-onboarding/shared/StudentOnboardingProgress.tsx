import { Check } from 'lucide-react'
import type { ReactNode } from 'react'

export interface OnboardingStep {
  label: string
  description: string
}

export default function StudentOnboardingProgress({
  steps,
  activeStep,
  onSelect,
}: {
  steps: OnboardingStep[]
  activeStep: number
  /** When set, completed steps become buttons that return to that step. */
  onSelect?: (index: number) => void
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
            {complete && onSelect ? (
              <button type="button" className="student-onboarding-step-button" onClick={() => onSelect(index)}>
                <StepContent step={step} marker={<Check size={16} />} />
                <span className="sr-only">(completed, go back)</span>
              </button>
            ) : (
              <StepContent step={step} marker={complete ? <Check size={16} /> : index + 1} />
            )}
          </li>
        )
      })}
    </ol>
  )
}

function StepContent({ step, marker }: { step: OnboardingStep; marker: ReactNode }) {
  return (
    <>
      <span className="student-onboarding-step-marker" aria-hidden="true">
        {marker}
      </span>
      <span className="student-onboarding-step-copy">
        <strong>{step.label}</strong>
        <small>{step.description}</small>
      </span>
    </>
  )
}
