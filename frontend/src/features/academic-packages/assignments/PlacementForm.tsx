import type { AcademicPackageCatalogue, PackageRecord } from '../../../types/academicPackages.ts'
import type { PackageWorkspaceState } from '../useAcademicPackages.ts'
import { PackageForm, Select, text } from '../forms/PackageFields.tsx'
import { rows, value } from '../packagePresentation.ts'

export default function PlacementForm({
  data,
  state,
  academicClass,
}: {
  data: AcademicPackageCatalogue
  state: PackageWorkspaceState
  academicClass: PackageRecord
}) {
  const registrations = rows(data, 'registrations').filter(
    (row) =>
      value(row, 'program_id') === value(academicClass, 'program_id') &&
      value(row, 'batch_id') === value(academicClass, 'batch_id'),
  )
  return (
    <PackageForm
      title="Place registered student in class"
      submit="Save class placement"
      busy={state.busy}
      onSave={(form) =>
        state.run('place_student', {
          class_id: value(academicClass, 'class_id'),
          registration_id: text(form, 'registration_id'),
        })
      }
    >
      <Select
        data={data}
        source="registrations"
        name="registration_id"
        title="Student registration"
        items={registrations}
      />
      <p className="package-helper">
        Reuse the student's existing registration for this teaching term. This records placement without creating
        another student identity.
      </p>
    </PackageForm>
  )
}
