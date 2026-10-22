import { useState } from 'react'
import type { AcademicPackageCatalogue, PackageRecord } from '../../../types/academicPackages.ts'
import type { PackageWorkspaceState } from '../useAcademicPackages.ts'
import { PackageForm, Reason, Select, text } from '../forms/PackageFields.tsx'
import { find, formatDeadline, isLocked, rows, value } from '../packagePresentation.ts'
import { PackageSubjects } from '../PackageSubjects.tsx'

export function availablePackages(data: AcademicPackageCatalogue, classId: string) {
  const ids = new Set(
    rows(data, 'class_packages')
      .filter((row) => value(row, 'class_id') === classId && row.enabled !== false)
      .map((row) => value(row, 'package_id')),
  )
  return rows(data, 'packages')
    .filter((row) => ids.has(value(row, 'package_id')))
    .map((row) => ({
      ...row,
      selection_code: value(
        rows(data, 'class_packages').find(
          (item) => value(item, 'class_id') === classId && value(item, 'package_id') === value(row, 'package_id'),
        ),
        'selection_code',
      ),
    }))
}

export function InitialAssignmentForm({
  data,
  state,
  academicClass,
}: {
  data: AcademicPackageCatalogue
  state: PackageWorkspaceState
  academicClass: PackageRecord
}) {
  const [packageId, setPackageId] = useState('')
  const classId = value(academicClass, 'class_id')
  const assigned = new Set(
    rows(data, 'assignments')
      .filter((row) => row.is_active !== false)
      .map((row) => value(row, 'placement_id')),
  )
  const placements = rows(data, 'placements').filter(
    (row) => value(row, 'class_id') === classId && !assigned.has(value(row, 'placement_id')),
  )
  const allowed =
    (data.capabilities.includes('assign') && academicClass.can_assign !== false) ||
    (data.capabilities.includes('select') && academicClass.student_choice_enabled === true)
  if (!allowed)
    return (
      <p className="package-lock">
        Your administration assigns the initial package for this class. Your existing selection remains unchanged.
      </p>
    )
  if (!placements.length)
    return (
      <p className="package-helper">
        No unassigned class placements. Current packages and change requests are shown below.
      </p>
    )
  return (
    <PackageForm
      title="Initial package assignment"
      submit="Assign all package subjects"
      busy={state.busy}
      onSave={(form) =>
        state.run('assign_package', {
          placement_id: text(form, 'placement_id'),
          package_id: text(form, 'package_id'),
        })
      }
    >
      <Select data={data} source="placements" name="placement_id" title="Student class placement" items={placements} />
      <Select
        data={data}
        source="packages"
        name="package_id"
        title="Complete package"
        items={availablePackages(data, classId)}
        selected={packageId}
        onChange={setPackageId}
      />
      <PackageSubjects data={data} packageId={packageId} />
      <p className="package-helper">
        This saves the complete subject combination. Later student changes require a request and authorized review.
      </p>
    </PackageForm>
  )
}

export function AssignmentChangeForm({
  data,
  state,
  assignment,
  academicClass,
}: {
  data: AcademicPackageCatalogue
  state: PackageWorkspaceState
  assignment: PackageRecord
  academicClass: PackageRecord
}) {
  const [packageId, setPackageId] = useState('')
  const direct = data.capabilities.includes('change') && academicClass.can_change !== false
  const request = data.capabilities.includes('request')
  if (isLocked(academicClass))
    return (
      <p className="package-lock">
        Package changes closed on {formatDeadline(academicClass)}. Your current package remains assigned. This deadline
        also applies to administrative changes and pending requests.
      </p>
    )
  if (!direct && !request) return null
  const packages = availablePackages(data, value(academicClass, 'class_id')).filter(
    (row) => value(row, 'package_id') !== value(assignment, 'package_id'),
  )
  return (
    <PackageForm
      title={direct ? 'Change assigned package' : 'Request package change'}
      submit={direct ? 'Apply complete package change' : 'Submit change request'}
      busy={state.busy}
      onSave={(form) => {
        const payload = {
          assignment_id: value(assignment, 'assignment_id'),
          package_id: text(form, 'package_id'),
          reason: text(form, 'reason'),
        }
        return direct
          ? state.run('change_package', { ...payload, expected_revision: Number(value(assignment, 'revision')) })
          : state.run('request_change', payload)
      }}
    >
      <Select
        data={data}
        source="packages"
        name="package_id"
        title="Requested package"
        items={packages}
        selected={packageId}
        onChange={setPackageId}
      />
      {find(data, 'packages', packageId) && <PackageSubjects data={data} packageId={packageId} />}
      <Reason />
      <p className="package-helper">
        Shared subjects and recorded attendance/marks are preserved. A pending request leaves your current package
        active.
      </p>
    </PackageForm>
  )
}
