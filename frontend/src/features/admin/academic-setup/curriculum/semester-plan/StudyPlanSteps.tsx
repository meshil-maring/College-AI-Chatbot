export default function StudyPlanSteps({ subjects = false }: { subjects?: boolean }) {
  return (
    <div className="study-plan-guide">
      <p>A curriculum is a study plan: choose what students study in each semester.</p>
      <ol aria-label="Prepare a study plan">
        <li aria-current={!subjects ? 'step' : undefined}>Create a draft and choose its number of semesters</li>
        <li aria-current={subjects ? 'step' : undefined}>Set up semesters and choose their subjects here</li>
        <li>Review and publish, then assign it to a batch</li>
      </ol>
    </div>
  )
}
