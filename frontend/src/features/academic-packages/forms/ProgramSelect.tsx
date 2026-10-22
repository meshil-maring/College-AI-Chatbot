import type { AcademicPackageCatalogue } from '../../../types/academicPackages.ts'
import { rows } from '../packagePresentation.ts'
import { Select } from './PackageFields.tsx'

export default function ProgramSelect({
  data,
  selected,
  onChange,
  onCreateProgram,
}: {
  data: AcademicPackageCatalogue
  selected?: string
  onChange?: (value: string) => void
  onCreateProgram?: () => void
}) {
  const available = rows(data, 'programs').some((row) => row.is_active !== false)
  return (
    <>
      <Select
        data={data}
        source="programs"
        name="program_id"
        title="Course / branch"
        selected={selected}
        onChange={onChange}
        emptyHint="Create or activate a degree program in College basics → Degree programs. Subjects are individual papers, such as DSA or ML."
      />
      {!available && onCreateProgram && (
        <button type="button" className="academic-secondary" onClick={onCreateProgram}>
          Set up a course / branch
        </button>
      )}
    </>
  )
}
