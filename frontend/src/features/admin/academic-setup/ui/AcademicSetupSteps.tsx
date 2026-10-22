import { ACADEMIC_STAGES, type AcademicStage } from '../academicSetupStages.ts'

export default function AcademicSetupSteps({
  stage,
  busy,
  onChange,
}: {
  stage: AcademicStage
  busy: boolean
  onChange: (stage: AcademicStage) => void
}) {
  return (
    <nav className="academic-workflow" aria-label="Academic setup workflow">
      {ACADEMIC_STAGES.map((item, index) => (
        <button
          key={item.key}
          type="button"
          aria-label={`${index + 1} ${item.title}`}
          aria-current={stage === item.key ? 'step' : undefined}
          disabled={busy}
          onClick={() => onChange(item.key)}
        >
          <span>{index + 1}</span>
          {item.title}
        </button>
      ))}
    </nav>
  )
}
