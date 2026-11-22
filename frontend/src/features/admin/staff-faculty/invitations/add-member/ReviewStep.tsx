import type { Department } from '../../../../../types/academicSetup.ts'
import { STAFF_CATEGORIES, employmentTypes, type MemberDraft } from './memberDraft.ts'

interface Props {
  draft: MemberDraft
  departments: Department[]
}

function formatDate(value: string) {
  if (!value) return ''
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString(undefined, { dateStyle: 'medium' })
}

/** Step 3: everything that will be saved, for the administrator to confirm. */
export default function ReviewStep({ draft, departments }: Props) {
  const name = (id: string) => departments.find((item) => item.department_id === id)?.name ?? 'Unknown department'
  const faculty = draft.role === 'faculty'
  const rows: [string, string][] = [
    ['Name', draft.full_name.trim()],
    ['Email', draft.email.trim().toLowerCase()],
    ['Phone', draft.phone.trim()],
    ['Employee ID', draft.employee_id.trim()],
    ['User type', faculty ? 'Teacher / Faculty' : 'Staff'],
    ['Designation', draft.designation.trim()],
    ['Joining date', formatDate(draft.joining_date)],
    ['Primary department', draft.department_id ? name(draft.department_id) : ''],
    ['Additional departments', draft.additional_department_ids.map(name).join(', ')],
    ...(faculty
      ? []
      : ([['Staff category', STAFF_CATEGORIES[draft.staff_category as keyof typeof STAFF_CATEGORIES] ?? '']] as [
          string,
          string,
        ][])),
    ['Employment type', employmentTypes(draft.role)[draft.employment_type] ?? ''],
    ['Employment start', formatDate(draft.employment_start_date)],
    ['Contract end', draft.employment_type === 'permanent' ? '' : formatDate(draft.contract_end_date)],
    ...(faculty
      ? ([
          ['Qualification', draft.qualification.trim()],
          ['Specialization', draft.specialization.trim()],
          ['Experience', draft.experience_years ? `${draft.experience_years} years` : ''],
        ] as [string, string][])
      : ([['Responsibilities', draft.responsibilities.join(', ')]] as [string, string][])),
    ['Account status', 'Invitation pending'],
  ]
  return (
    <>
      <p className="text-sm text-muted">
        Check the details. We email them a link to set their password; their account becomes active once they accept.
      </p>
      <dl className="grid gap-x-4 gap-y-2 rounded-lg border border-line p-4 text-sm sm:grid-cols-[minmax(0,10rem)_1fr]">
        {rows
          .filter(([, value]) => value)
          .map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="text-muted">{label}</dt>
              <dd className="break-words text-content">{value}</dd>
            </div>
          ))}
      </dl>
    </>
  )
}
