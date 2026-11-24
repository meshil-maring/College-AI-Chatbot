import { useRef, useState } from 'react'
import type { StudentIdentityReviewResponse, StudentInvitationInput } from '../../../../types/admin/students.ts'
import { reviewStudentIdentity } from '../../../../services/admin/students.ts'

export function useStudentIdentityConflictReview(accessToken: string) {
  const [identityReview, setIdentityReview] = useState<StudentIdentityReviewResponse | null>(null)
  const [identityReviewError, setIdentityReviewError] = useState('')
  const [identityReviewing, setIdentityReviewing] = useState(false)
  // Ignore lookups that finish after the details changed or a newer lookup started.
  const generation = useRef(0)

  function clear() {
    generation.current += 1
    setIdentityReview(null)
    setIdentityReviewError('')
    setIdentityReviewing(false)
  }

  async function lookup(student: StudentInvitationInput) {
    const current = ++generation.current
    setIdentityReview(null)
    setIdentityReviewError('')
    setIdentityReviewing(true)
    try {
      const review = await reviewStudentIdentity(accessToken, {
        email: student.email.trim().toLowerCase(),
        register_number: student.register_number.trim(),
        university_roll_number: student.university_roll_number?.trim() || null,
      })
      if (current === generation.current) setIdentityReview(review)
    } catch {
      if (current !== generation.current) return
      setIdentityReviewError(
        'The conflict could not be matched to institution records. Refresh All Students or contact your administrator.',
      )
    } finally {
      if (current === generation.current) setIdentityReviewing(false)
    }
  }

  return { identityReview, identityReviewError, identityReviewing, lookup, clear }
}
