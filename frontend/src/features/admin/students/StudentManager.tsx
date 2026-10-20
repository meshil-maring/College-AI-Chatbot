import { ArrowRight, ChevronRight, Info, Upload, UserPlus } from 'lucide-react'
import { useApiQuery } from '../../../hooks/useApiQuery.ts'
import { useAuth } from '../../auth/AuthProvider.tsx'
import { hasPermission } from '../../auth/permissions.ts'
import { listStudents } from '../../../services/adminApi.ts'
import type { Student } from '../../../types/admin.ts'
import AdminApprovals from './AdminApprovals.tsx'
import StudentDirectory from './StudentDirectory.tsx'
import StudentImport from './StudentImport.tsx'
import type { StudentSection } from './studentSections.ts'

/** Fetch every page so totals and duplicate checks share the same institution scope. */
export async function loadStudentDirectory(
  token: string,
  institutionId: string,
): Promise<Student[]> {
  const result: Student[] = []
  for (let offset = 0; offset < 100_000; offset += 100) {
    const page = await listStudents(token, institutionId, {
      limit: 100,
      offset,
    })
    result.push(...page)
    if (page.length < 100) return result
  }
  throw new Error(
    'The directory is too large to load in one view. Please contact your administrator.',
  )
}

export default function StudentManager({
  section,
  onSection,
  search,
  onSearch,
}: {
  section: StudentSection
  onSection: (section: StudentSection) => void
  search: string
  onSearch: (search: string) => void
}) {
  const { accessToken, user } = useAuth()
  const institutionId = user?.institution_id ?? null
  const studentsQuery = useApiQuery<Student[]>(
    ['admin', 'students', accessToken, institutionId],
    () => loadStudentDirectory(accessToken as string, institutionId as string),
    accessToken !== null && institutionId !== null,
    { cache: 'navigation' },
  )
  if (institutionId === null || accessToken === null)
    return (
      <section className="students-empty" role="status">
        <h1>Students</h1>
        <p>
          {institutionId === null
            ? 'No institution is linked to your administrator account, so there are no students to manage yet.'
            : 'Your session could not be verified. Please sign in again.'}
        </p>
      </section>
    )
  const students = studentsQuery.data ?? []
  const canApprove =
    hasPermission(user?.effective_permissions, 'students.read') &&
    hasPermission(user?.effective_permissions, 'students.approve') &&
    hasPermission(user?.effective_permissions, 'students.reject')
  const error = studentsQuery.isError
    ? studentsQuery.error instanceof Error
      ? studentsQuery.error.message
      : 'Failed to load students.'
    : null
  if (section === 'requests')
    return (
      <section className="students-content">
        <div className="students-breadcrumb">
          <button onClick={() => onSection('all')}>Students</button>
          <ChevronRight />
          <span aria-current="page">Registration Requests</span>
        </div>
        <div className="students-title">
          <div>
            <h1>Registration Requests</h1>
            <p>
              Review student registrations and welcome approved students to your
              institution.
            </p>
          </div>
        </div>
        {canApprove ? (
          <AdminApprovals accessToken={accessToken} />
        ) : (
          <div className="students-alert" role="status">
            <Info />
            <span>
              Your account does not have permission to manage student approvals.
            </span>
          </div>
        )}
      </section>
    )
  if (section === 'add')
    return (
      <section className="students-content">
        <div className="students-breadcrumb">
          <button onClick={() => onSection('all')}>Students</button>
          <ChevronRight />
          <span aria-current="page">Add Student</span>
        </div>
        <div className="students-title">
          <div>
            <h1>Add Student</h1>
            <p>Choose how to bring students into your institution.</p>
          </div>
        </div>
        <div className="students-onboarding-grid">
          <article className="students-onboarding-card">
            <div className="students-upload-icon">
              <UserPlus />
            </div>
            <h2>Review a student registration</h2>
            <p>
              Students register through the college’s sign-up flow. Review their
              pending registration and approve their access from Registration
              Requests.
            </p>
            <button
              className="students-button primary"
              disabled={!canApprove}
              onClick={() => onSection('requests')}
            >
              Registration Requests
              <ArrowRight />
            </button>
            {!canApprove && (
              <small>Student approval permission is required.</small>
            )}
          </article>
          <article className="students-onboarding-card">
            <div className="students-upload-icon">
              <Upload />
            </div>
            <h2>Prepare a bulk import</h2>
            <p>
              Upload a spreadsheet, review student details, and download a
              validation report. Bulk saving is not available yet.
            </p>
            <button
              className="students-button"
              onClick={() => onSection('import')}
            >
              Upload Student File
              <ArrowRight />
            </button>
          </article>
        </div>
        <div className="students-format">
          <Info />
          <p>
            Direct student creation from this workspace is not available yet.
            Existing student accounts and academic records remain accessible in
            All Students.
          </p>
        </div>
      </section>
    )
  if (section === 'import')
    return (
      <>
        <StudentImport
          students={students}
          directoryReady={studentsQuery.isSuccess && !studentsQuery.isFetching}
          onBack={() => onSection('all')}
        />
        {error && (
          <div className="students-alert error" role="alert">
            <span>Existing student checks could not be completed: {error}</span>
            <button
              className="students-button"
              onClick={() => void studentsQuery.refetch()}
            >
              Retry
            </button>
          </div>
        )}
      </>
    )
  return (
    <StudentDirectory
      students={students}
      loading={studentsQuery.isPending}
      refreshing={studentsQuery.isFetching}
      error={error}
      search={search}
      onSearch={onSearch}
      onRefresh={() => void studentsQuery.refetch()}
      onSection={onSection}
    />
  )
}
