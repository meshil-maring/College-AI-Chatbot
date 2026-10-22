import type { AcademicPackageCatalogue } from '../../../types/academicPackages.ts'
import type { PackageWorkspaceState } from '../useAcademicPackages.ts'
import { PackageForm, Reason, text } from '../forms/PackageFields.tsx'
import { classForAssignment, find, formatDeadline, isLocked, labelForId, rows, value } from '../packagePresentation.ts'
import { PackageSubjects } from '../PackageSubjects.tsx'

export default function PackageRequests({
  data,
  state,
}: {
  data: AcademicPackageCatalogue
  state: PackageWorkspaceState
}) {
  const requests = rows(data, 'requests')
  return (
    <section className="package-records" aria-label="Package change requests">
      {!requests.length && <p className="academic-empty">No change requests in your academic scope.</p>}
      {requests.map((request) => {
        const assignment = find(data, 'assignments', value(request, 'assignment_id'))
        const academicClass = assignment ? classForAssignment(data, assignment) : undefined
        const locked = isLocked(academicClass)
        const pending = value(request, 'status').toLowerCase() === 'pending'
        const packageId = value(request, 'package_id') || value(request, 'target_package_id')
        return (
          <article key={value(request, 'request_id')} className="package-record">
            <h3>
              {assignment ? labelForId(data, 'assignments', value(request, 'assignment_id')) : 'Package change request'}
            </h3>
            <p>
              <span className="package-badge">{pending && locked ? 'Expired' : value(request, 'status')}</span>
            </p>
            <p>Requested package: {labelForId(data, 'packages', packageId)}</p>
            <p>Student reason: {value(request, 'reason')}</p>
            {value(request, 'decision_reason') && <p>Decision: {value(request, 'decision_reason')}</p>}
            <PackageSubjects data={data} packageId={packageId} />
            {pending && locked && (
              <p className="package-lock">
                Package changes closed on {formatDeadline(academicClass)}. This request cannot be approved after the
                deadline.
              </p>
            )}
            {pending && !locked && data.capabilities.includes('review') && academicClass?.can_review !== false && (
              <PackageForm
                title="Review change request"
                submit="Save decision"
                busy={state.busy}
                onSave={(form) =>
                  state.run('review_request', {
                    request_id: value(request, 'request_id'),
                    approve: text(form, 'decision') === 'approve',
                    reason: text(form, 'reason'),
                  })
                }
              >
                <label>
                  Decision
                  <select name="decision" required>
                    <option value="approve">Approve complete package change</option>
                    <option value="reject">Reject request</option>
                  </select>
                </label>
                <Reason />
                <p className="package-helper">
                  Approval rechecks eligibility, the current assignment, teaching groups, capacity and the deadline
                  before applying any change.
                </p>
              </PackageForm>
            )}
          </article>
        )
      })}
    </section>
  )
}
