import type { AcademicSection } from '../../../../types/academicStructure.ts'

export default function SectionSubjectFilter({
  sections,
  value,
  onChange,
}: {
  sections: AcademicSection[]
  value: string
  onChange: (sectionId: string) => void
}) {
  return (
    <label className="structure-section-filter">
      <span>Choose an academic section</span>
      <select
        aria-label="Choose an academic section"
        value={value}
        disabled={!sections.length}
        onChange={(event) => onChange(event.currentTarget.value)}
      >
        <option value="">Select a section</option>
        {sections.map((section) => (
          <option key={section.academic_section_id} value={section.academic_section_id}>
            {section.name} ({section.code})
          </option>
        ))}
      </select>
      <small>
        Select the class section whose available subjects you want to review or manage.
        {!sections.length && ' No active sections are available yet.'}
      </small>
    </label>
  )
}
