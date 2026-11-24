import { useState } from 'react'
import type { StudentInvitationInput } from '../../../../types/admin/students.ts'
import { createStudentInvitation } from '../../../../services/admin/students.ts'
import { refreshStudentInvitations } from '../invitations/studentInvitationQueries.ts'
import { useStudentIdentityConflictReview } from './useStudentIdentityConflictReview.ts'

function emptyStudent(): StudentInvitationInput {
  return { student_name: '', register_number: '', university_roll_number: null, email: '' }
}

/** Placement → details → review → result state for registering one student. */
export function useSingleRegistration(accessToken: string, identity: string) {
  const conflictReview = useStudentIdentityConflictReview(accessToken)
  const [sectionId, setSectionId] = useState('')
  const [step, setStep] = useState(0)
  const [student, setStudent] = useState<StudentInvitationInput>(emptyStudent)
  const [delivery, setDelivery] = useState<'sent' | 'failed'>('sent')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function goTo(next: number) {
    setError('')
    setStep(next)
  }
  function setField(field: keyof StudentInvitationInput, value: string) {
    setStudent((current) => ({ ...current, [field]: value }))
    conflictReview.clear()
  }

  async function submit() {
    if (!sectionId) return
    setBusy(true)
    setError('')
    conflictReview.clear()
    try {
      const result = await createStudentInvitation(accessToken, sectionId, {
        ...student,
        email: student.email.trim().toLowerCase(),
        student_name: student.student_name.trim(),
        register_number: student.register_number.trim(),
        university_roll_number: student.university_roll_number?.trim() || null,
      })
      setDelivery(result.delivery_status)
      setStep(3)
      refreshStudentInvitations(identity)
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Student invitation could not be created.'
      setError(message)
      if (message.toLowerCase().includes('already in use')) await conflictReview.lookup(student)
    } finally {
      setBusy(false)
    }
  }

  function reset() {
    setStudent(emptyStudent())
    setStep(0)
    setSectionId('')
    setError('')
    conflictReview.clear()
  }

  return {
    sectionId,
    setSectionId,
    step,
    goTo,
    student,
    setField,
    delivery,
    error,
    busy,
    identityReview: conflictReview.identityReview,
    identityReviewError: conflictReview.identityReviewError,
    identityReviewing: conflictReview.identityReviewing,
    submit,
    reset,
  }
}

export type SingleRegistration = ReturnType<typeof useSingleRegistration>
