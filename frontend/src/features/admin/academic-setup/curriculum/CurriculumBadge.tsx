export default function CurriculumBadge({ active }: { active: boolean }) {
  return (
    <span className={`curriculum-badge${active ? ' is-active' : ''}`}>
      <span aria-hidden="true" />
      {active ? 'Active' : 'Inactive'}
    </span>
  )
}
