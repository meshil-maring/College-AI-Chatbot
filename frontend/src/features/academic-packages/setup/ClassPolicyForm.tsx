import type { PackageRecord } from '../../../types/academicPackages.ts'
import type { PackageWorkspaceState } from '../useAcademicPackages.ts'
import { Checkbox, PackageForm, checked, text } from '../forms/PackageFields.tsx'
import { isLocked, value } from '../packagePresentation.ts'

export default function ClassPolicyForm({
  state,
  academicClass,
}: {
  state: PackageWorkspaceState
  academicClass: PackageRecord
}) {
  const locked = isLocked(academicClass)
  const deadline = value(academicClass, 'change_cutoff')
  const date = Date.parse(deadline)
  const inputDeadline = Number.isFinite(date) ? new Date(date + 330 * 60_000).toISOString().slice(0, 16) : ''
  return (
    <PackageForm
      title="Class selection rules"
      submit="Save selection rules"
      busy={state.busy}
      onSave={(form) =>
        state.run('save_class', {
          class_id: value(academicClass, 'class_id'),
          program_id: value(academicClass, 'program_id'),
          batch_id: value(academicClass, 'batch_id'),
          semester_id: value(academicClass, 'semester_id'),
          study_semester: Number(value(academicClass, 'study_semester')),
          section_code: value(academicClass, 'section_code'),
          curriculum_id: value(academicClass, 'curriculum_id'),
          student_choice_enabled: checked(form, 'student_choice_enabled'),
          change_cutoff:
            !locked && text(form, 'change_cutoff') && text(form, 'change_cutoff') !== inputDeadline
              ? `${text(form, 'change_cutoff')}:00+05:30`
              : deadline,
        })
      }
    >
      <Checkbox
        name="student_choice_enabled"
        title="Allow students to choose their initial package"
        defaultChecked={academicClass.student_choice_enabled === true}
      />
      {!locked && (
        <label>
          Package change cutoff (IST)
          <input type="datetime-local" name="change_cutoff" defaultValue={inputDeadline} max={inputDeadline} required />
        </label>
      )}
      <p className="package-helper">
        The deadline can only move earlier and can never exceed the calendar midpoint. Once closed, it cannot be
        reopened. The initial-choice setting never changes existing assignments.
      </p>
    </PackageForm>
  )
}
