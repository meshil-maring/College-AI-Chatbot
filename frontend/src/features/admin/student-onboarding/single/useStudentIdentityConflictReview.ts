import { useState } from 'react'
import type { StudentIdentityReviewResponse, StudentInvitationInput } from '../../../../types/admin/students.ts'
import { reviewStudentIdentity } from '../../../../services/admin/students.ts'

export function useStudentIdentityConflictReview(accessToken: string) {
  const [identityReview, setIdentityReview] = useState<StudentIdentityReviewResponse | null>(null)
  const [identityReviewError, setIdentityReviewError] = useState('')
  const [identityReviewing, setIdentityReviewing] = useState(false)

  function clear() {
    setIdentityReview(null)
    setIdentityReviewError('')
    setIdentityReviewing(false)
  }

  async function lookup(student: StudentInvitationInput) {
    setIdentityReview(null)
    setIdentityReviewError('')
    setIdentityReviewing(true)
    try {
      setIdentityReview(
        await reviewStudentIdentity(accessToken, {
          email: student.email.trim().toLowerCase(),
          register_number: student.register_number.trim(),
          university_roll_number: student.university_roll_number?.trim() || null,
        }),
      )
    } catch {
      setIdentityReviewError(
        'The conflict could not be matched to institution records. Refresh All Students or contact your administrator.',
      )
    } finally {
      setIdentityReviewing(false)
    }
  }

  return { identityReview, identityReviewError, identityReviewing, lookup, clear }
}
