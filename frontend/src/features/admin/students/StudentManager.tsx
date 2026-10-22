import { useApiQuery } from '../../../hooks/useApiQuery.ts'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import { usePermissions } from '../../auth/access/usePermissions.ts'
import { canOpenPackageWorkspace } from '../../academic-packages/packageNavigation.ts'
import { adminStudentWorkspaceApi } from '../../../services/admin/adminStudentWorkspaceApi.ts'
import { StudentWorkspace } from '../../faculty/students/FacultyStudents.tsx'
import { StudentWorkspaceContext } from '../../students/StudentWorkspaceContext.tsx'
import { StudentsPageHeader } from '../../students/StudentsUI.tsx'
import { STUDENT_PAGES, type StudentPage, type StudentRegistrationMethod } from '../../students/studentsNavigation.ts'
import AdminApprovals from './AdminApprovals.tsx'

export default function StudentManager({
  section,
  sectionId,
  onNavigate,
  registrationMethod,
  onRegistrationMethod,
  search = '',
}: {
  section: StudentPage
  sectionId: string
  onNavigate: (page: StudentPage, sectionId: string, replace?: boolean) => void
  registrationMethod: StudentRegistrationMethod
  onRegistrationMethod: (method: StudentRegistrationMethod) => void
  search?: string
}) {
  const { accessToken, user } = useAuth()
  const tenant = user?.institution_id
  const { can, canAll } = usePermissions()
  const pageLabel = STUDENT_PAGES.find((item) => item.key === section)!.label
  const canRead = can('students', 'read')
  const canBrowse = canAll('students.read', 'attendance.read')
  const canApprove = canAll('students.read', 'students.approve', 'students.reject')
  const sections = useApiQuery(
    ['admin', 'students', accessToken, tenant, 'sections'],
    () => adminStudentWorkspaceApi.getSections(accessToken as string),
    !!accessToken && !!tenant && canRead && (canBrowse || section === 'register' || section === 'subject-assignment'),
  )
  const assignments = sections.isError ? [] : (sections.data ?? [])
  const selected = sectionId
    ? assignments.find((item) => item.section_id === sectionId)
    : section === 'register'
      ? assignments.find((item) => item.can_manage)
      : assignments[0]

  if (!tenant || !accessToken)
    return (
      <section className="students-empty" role="status">
        <h1>Students</h1>
        <p>
          {!tenant
            ? 'No institution is linked to your administrator account.'
            : 'Your session could not be verified. Please sign in again.'}
        </p>
      </section>
    )
  return (
    <StudentWorkspaceContext.Provider value={adminStudentWorkspaceApi}>
      {canBrowse || ((section === 'register' || section === 'subject-assignment') && canRead) ? (
        <StudentWorkspace
          accessToken={accessToken}
          page={section}
          sectionId={sectionId}
          assignmentsQuery={sections}
          assignments={assignments}
          selected={selected}
          onNavigate={onNavigate}
          registrationMethod={registrationMethod}
          onRegistrationMethod={onRegistrationMethod}
          initialSearch={search}
          packageAccess={canOpenPackageWorkspace(user?.effective_permissions)}
        />
      ) : (
        <section className="students-content students-scope">
          <StudentsPageHeader page={pageLabel} title="Students" />
          {!(section === 'waiting-approval' && canApprove) && (
            <p className="students-alert" role="status">
              Your account does not have permission to view student rosters and attendance.
            </p>
          )}
        </section>
      )}
      {section === 'waiting-approval' && canApprove && (
        <div className="mt-6">
          <AdminApprovals accessToken={accessToken} />
        </div>
      )}
    </StudentWorkspaceContext.Provider>
  )
}
