import BulkImportPage from './bulk/BulkImportPage.tsx'
import AddStudentPage from './single/AddStudentPage.tsx'
import './studentOnboarding.css'

/** Admin student onboarding: Add Student (one at a time) or Bulk Import (spreadsheet). */
export default function StudentOnboardingPage({
  accessToken,
  identity,
  canManage,
  canReview = false,
  bulkOnly = false,
}: {
  accessToken: string
  identity: string
  canManage: boolean
  canReview?: boolean
  bulkOnly?: boolean
}) {
  if (!canManage) {
    return (
      <p role="status">Student creation requires Students create/approve/update/read and Courses manage permissions.</p>
    )
  }
  return bulkOnly ? (
    <BulkImportPage accessToken={accessToken} identity={identity} />
  ) : (
    <AddStudentPage accessToken={accessToken} identity={identity} canReview={canReview} />
  )
}
