import { useState } from 'react'
import type { AcademicPackageCatalogue, PackageRecord } from '../../../types/academicPackages.ts'
import type { PackageWorkspaceState } from '../useAcademicPackages.ts'
import { Checkbox, PackageForm, Select, checked, text } from '../forms/PackageFields.tsx'
import { find, rows, value } from '../packagePresentation.ts'

export default function ClassRelationships({
  data,
  state,
  academicClass,
}: {
  data: AcademicPackageCatalogue
  state: PackageWorkspaceState
  academicClass: PackageRecord
}) {
  const classId = value(academicClass, 'class_id')
  const [subjectId, setSubjectId] = useState('')
  const subjects = rows(data, 'curriculum_subjects').filter(
    (row) =>
      value(row, 'curriculum_id') === value(academicClass, 'curriculum_id') &&
      value(row, 'study_semester') === value(academicClass, 'study_semester'),
  )
  const packages = rows(data, 'packages').filter(
    (row) =>
      value(row, 'curriculum_id') === value(academicClass, 'curriculum_id') &&
      value(row, 'study_semester') === value(academicClass, 'study_semester'),
  )
  const subject = find(data, 'curriculum_subjects', subjectId)
  const mappedSections = new Set(
    rows(data, 'class_subjects')
      .filter((row) => value(row, 'class_id') === classId)
      .map((row) => value(row, 'section_id')),
  )
  const responsibilities = rows(data, 'responsibilities').filter(
    (row) =>
      value(row, 'program_id') === value(academicClass, 'program_id') &&
      value(row, 'academic_year_id') === value(academicClass, 'academic_year_id') &&
      value(row, 'semester_id') === value(academicClass, 'semester_id') &&
      mappedSections.has(value(row, 'section_id')),
  )
  const sections = rows(data, 'sections').filter(
    (row) =>
      (!value(row, 'course_id') || value(row, 'course_id') === value(subject, 'course_id')) &&
      (!value(row, 'program_id') || value(row, 'program_id') === value(academicClass, 'program_id')) &&
      (!value(row, 'semester_id') || value(row, 'semester_id') === value(academicClass, 'semester_id')),
  )
  return (
    <>
      <section className="academic-panel package-card">
        <h3>Prepare subject teaching groups</h3>
        <p className="package-helper">
          An administrator can prepare offerings and a teaching group for every shared core and enabled-package subject
          in this class. Existing subject mappings are kept.
        </p>
        {data.capabilities.includes('prepare_teaching') ? (
          <button
            type="button"
            className="academic-primary"
            disabled={state.busy}
            onClick={() => void state.run('prepare_class_teaching', { class_id: classId }).catch(() => {})}
          >
            Prepare teaching groups
          </button>
        ) : (
          <p className="package-helper">Ask an administrator with teaching setup access to prepare these groups.</p>
        )}
      </section>
      <PackageForm
        title="Available class package"
        busy={state.busy}
        onSave={(form) =>
          state.run('set_class_package', {
            class_id: classId,
            package_id: text(form, 'package_id'),
            enabled: checked(form, 'enabled'),
          })
        }
      >
        <Select data={data} source="packages" name="package_id" title="Package" items={packages} />
        <Checkbox name="enabled" title="Available for new assignments and change requests" defaultChecked />
      </PackageForm>
      <details className="package-mapping-details">
        <summary>Teaching group mapping details</summary>
        <PackageForm
          title="Map subject teaching group"
          busy={state.busy}
          onSave={(form) =>
            state.run('set_class_subject', {
              class_id: classId,
              curriculum_subject_id: text(form, 'curriculum_subject_id'),
              section_id: text(form, 'section_id'),
            })
          }
        >
          <Select
            data={data}
            source="curriculum_subjects"
            name="curriculum_subject_id"
            title="Curriculum subject"
            items={subjects}
            selected={subjectId}
            onChange={setSubjectId}
          />
          <Select
            data={data}
            source="sections"
            name="section_id"
            title="Existing subject teaching section"
            items={subjectId ? sections : []}
          />
          <p className="package-helper">
            Review or adjust the teaching groups prepared for this class. Every core and enabled-package subject needs a
            mapping before assigning students. Faculty use these subject teaching groups.
          </p>
        </PackageForm>
      </details>
      <PackageForm
        title="Assign class responsibility"
        busy={state.busy}
        onSave={(form) =>
          state.run('set_class_responsibility', {
            class_id: classId,
            responsibility_id: text(form, 'responsibility_id'),
            enabled: checked(form, 'enabled'),
          })
        }
      >
        <Select
          data={data}
          source="responsibilities"
          name="responsibility_id"
          title="Existing class incharge responsibility"
          items={responsibilities}
        />
        <p className="package-helper">Choose an incharge assigned to one of this class's mapped teaching groups.</p>
        <Checkbox name="enabled" title="Enable responsibility for this exact class" defaultChecked />
      </PackageForm>
    </>
  )
}
