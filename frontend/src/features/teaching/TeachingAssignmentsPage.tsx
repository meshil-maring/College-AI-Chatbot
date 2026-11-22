import { Feedback } from '../admin/staff-faculty/StaffFacultyUI.tsx'
import AssignTeachingForm from './AssignTeachingForm.tsx'
import TeachingAssignmentList from './TeachingAssignmentList.tsx'
import TeachingRequests from './TeachingRequests.tsx'
import { useTeaching } from './useTeaching.ts'

/**
 * Who teaches which subject offering. Administrators see everything; a Head of
 * Department sees their departments and their own teachers. Teaching outside a
 * teacher's departments waits for the subject department's Head to approve it.
 */
export default function TeachingAssignmentsPage({ accessToken }: { accessToken: string }) {
  const model = useTeaching(accessToken)
  return (
    <section aria-label="Teaching assignments" className="space-y-4">
      <Feedback error={model.error} success={model.notice} onDismiss={model.dismiss} />
      {model.optionsError ? (
        <p role="alert" className="text-sm text-danger">
          {model.optionsError}
        </p>
      ) : null}
      <TeachingRequests model={model} />
      <AssignTeachingForm model={model} />
      <TeachingAssignmentList model={model} />
      <p className="text-xs text-muted">
        Department membership does not give teaching access by itself. Teaching assignments are recorded for planning;
        they do not unlock attendance or marks yet.
      </p>
    </section>
  )
}
