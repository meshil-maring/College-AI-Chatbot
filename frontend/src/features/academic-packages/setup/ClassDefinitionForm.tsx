import { useState } from 'react'
import type { AcademicPackageCatalogue } from '../../../types/academicPackages.ts'
import type { PackageWorkspaceState } from '../useAcademicPackages.ts'
import { Checkbox, Input, PackageForm, Select, checked, number, text } from '../forms/PackageFields.tsx'
import { rows, value } from '../packagePresentation.ts'
import ProgramSelect from '../forms/ProgramSelect.tsx'

export default function ClassDefinitionForm({
  data,
  state,
  onCreateProgram,
}: {
  data: AcademicPackageCatalogue
  state: PackageWorkspaceState
  onCreateProgram?: () => void
}) {
  const [program, setProgram] = useState('')
  const [studySemester, setStudySemester] = useState('1')
  const readyCurricula = rows(data, 'curricula').filter(
    (row) =>
      value(row, 'program_id') === program &&
      rows(data, 'packages').some(
        (item) =>
          value(item, 'curriculum_id') === value(row, 'curriculum_id') &&
          value(item, 'study_semester') === studySemester,
      ),
  )
  return (
    <PackageForm
      title="Create shared class"
      busy={state.busy}
      onSave={(form) =>
        state.run('save_class', {
          program_id: text(form, 'program_id'),
          batch_id: text(form, 'batch_id'),
          semester_id: text(form, 'semester_id'),
          study_semester: number(form, 'study_semester'),
          section_code: text(form, 'section_code'),
          curriculum_id: text(form, 'curriculum_id'),
          student_choice_enabled: checked(form, 'student_choice_enabled'),
          change_cutoff: text(form, 'change_cutoff') ? `${text(form, 'change_cutoff')}:00+05:30` : null,
        })
      }
    >
      <ProgramSelect data={data} selected={program} onChange={setProgram} onCreateProgram={onCreateProgram} />
      <Select
        data={data}
        source="batches"
        name="batch_id"
        title="Admission batch"
        items={rows(data, 'batches').filter((row) => value(row, 'program_id') === program)}
      />
      <Select data={data} source="semesters" name="semester_id" title="Dated teaching term" />
      <label>
        Study semester
        <input
          name="study_semester"
          type="number"
          min={1}
          max={30}
          value={studySemester}
          required
          onChange={(event) => setStudySemester(event.target.value)}
        />
      </label>
      <Input name="section_code" title="Class section code" />
      <Select data={data} source="curricula" name="curriculum_id" title="Curriculum version" items={readyCurricula} />
      <Checkbox name="student_choice_enabled" title="Allow students to choose their initial package" />
      <p className="package-helper">
        Creating a class freezes this curriculum version. Finish its subjects and all packages first.
      </p>
      <label>
        Package change cutoff (IST, optional)
        <input name="change_cutoff" type="datetime-local" />
      </label>
      <p className="package-helper">
        An empty cutoff uses the calendar midpoint of the term. An earlier cutoff is allowed. Changes close for everyone
        at that instant; first-time assignments remain allowed.
      </p>
    </PackageForm>
  )
}
