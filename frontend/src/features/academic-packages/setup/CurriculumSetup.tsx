import { useState } from 'react'
import type { AcademicPackageCatalogue } from '../../../types/academicPackages.ts'
import type { PackageWorkspaceState } from '../useAcademicPackages.ts'
import { Checkbox, Input, PackageForm, Select, checked, number, text } from '../forms/PackageFields.tsx'
import { canManage, find, label, rows, value } from '../packagePresentation.ts'
import { PackageSubjects } from '../PackageSubjects.tsx'
import ProgramSelect from '../forms/ProgramSelect.tsx'

export default function CurriculumSetup({
  data,
  state,
  onCreateProgram,
}: {
  data: AcademicPackageCatalogue
  state: PackageWorkspaceState
  onCreateProgram?: () => void
}) {
  const [curriculumId, setCurriculumId] = useState('')
  const [semester, setSemester] = useState('1')
  const selected = find(data, 'curricula', curriculumId)
  const frozen =
    selected?.locked === true || rows(data, 'classes').some((row) => value(row, 'curriculum_id') === curriculumId)
  const subjects = rows(data, 'curriculum_subjects').filter(
    (row) => value(row, 'curriculum_id') === curriculumId && value(row, 'study_semester') === semester,
  )
  const packages = rows(data, 'packages').filter(
    (row) => value(row, 'curriculum_id') === curriculumId && value(row, 'study_semester') === semester,
  )
  const manage = canManage(data, 'curriculum')
  return (
    <div className="package-layout">
      <div>
        {manage && (
          <PackageForm
            title="Create named curriculum"
            busy={state.busy}
            onSave={(form) =>
              state.run('save_curriculum', {
                program_id: text(form, 'program_id'),
                name: text(form, 'name'),
                code: text(form, 'code'),
                version: number(form, 'version'),
              })
            }
          >
            <ProgramSelect data={data} onCreateProgram={onCreateProgram} />
            <Input name="name" title="Curriculum name" />
            <Input name="code" title="Curriculum code" />
            <Input name="version" title="Version" type="number" max={1000} defaultValue={1} />
            <p className="package-helper">Create a new version to revise a curriculum already used by a class.</p>
          </PackageForm>
        )}
        <section className="academic-panel package-card package-form">
          <h3>Curriculum detail</h3>
          <Select
            data={data}
            source="curricula"
            name="view_curriculum"
            title="Curriculum"
            selected={curriculumId}
            onChange={setCurriculumId}
          />
          <label>
            Study semester
            <input
              type="number"
              min={1}
              max={30}
              value={semester}
              onChange={(event) => setSemester(event.target.value)}
            />
          </label>
          <p className="package-helper">
            Study semester is the stage in the degree. Class Setup connects it to a dated teaching term.
          </p>
        </section>
        {selected && manage && !frozen && (
          <PackageForm
            title="Add curriculum subject"
            busy={state.busy}
            onSave={(form) =>
              state.run('set_curriculum_subject', {
                curriculum_id: curriculumId,
                course_id: text(form, 'course_id'),
                study_semester: Number(semester),
                course_type: text(form, 'course_type'),
                is_core: checked(form, 'is_core'),
              })
            }
          >
            <Select data={data} source="subjects" name="course_id" title="Subject" />
            <label>
              Subject type
              <select name="course_type" required>
                {['core', 'elective', 'open_elective', 'skill', 'project'].map((type) => (
                  <option key={type} value={type}>
                    {type.replaceAll('_', ' ')}
                  </option>
                ))}
              </select>
            </label>
            <Checkbox name="is_core" title="Required shared core in every package" />
          </PackageForm>
        )}
      </div>
      <div>
        {!selected ? (
          <p className="academic-empty">Choose a curriculum to organize its subjects and fixed packages.</p>
        ) : (
          <>
            <section className="academic-panel package-card">
              <h3>{label(data, 'curricula', selected)}</h3>
              {frozen && (
                <p className="package-lock">
                  This curriculum is used by a class. Its subjects and packages are frozen; create a new version for
                  changes.
                </p>
              )}
              <h4>Semester {semester} subjects</h4>
              {subjects.length ? (
                <ul className="package-subject-list">
                  {subjects.map((row) => (
                    <li key={value(row, 'curriculum_subject_id')}>{label(data, 'curriculum_subjects', row)}</li>
                  ))}
                </ul>
              ) : (
                <p className="package-helper">No subjects in this study semester yet.</p>
              )}
            </section>
            {manage && !frozen && (
              <PackageForm
                title="Create fixed subject package"
                busy={state.busy}
                onSave={(form) =>
                  state.run('save_package', {
                    curriculum_id: curriculumId,
                    study_semester: Number(semester),
                    name: text(form, 'name'),
                    code: text(form, 'code'),
                    curriculum_subject_ids: form.getAll('curriculum_subject_ids').map(String),
                  })
                }
              >
                <Input name="name" title="Package name" />
                <Input name="code" title="Package code" />
                <fieldset>
                  <legend>Package subjects</legend>
                  {subjects
                    .filter((row) => row.is_core !== true)
                    .map((row) => (
                      <label key={value(row, 'curriculum_subject_id')}>
                        <input
                          type="checkbox"
                          name="curriculum_subject_ids"
                          value={value(row, 'curriculum_subject_id')}
                        />
                        {label(data, 'curriculum_subjects', row)}
                      </label>
                    ))}
                  <p className="package-helper">
                    Select a complete subject combination. All shared core subjects are included automatically.
                  </p>
                </fieldset>
              </PackageForm>
            )}
            <div className="package-records">
              {packages.map((row) => (
                <article className="package-record" key={value(row, 'package_id')}>
                  <h3>{label(data, 'packages', row)}</h3>
                  <PackageSubjects data={data} packageId={value(row, 'package_id')} />
                </article>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
