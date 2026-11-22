import { useState } from 'react'
import type { MemberInvitationCreate } from '../../../../../types/admin.ts'
import {
  emptyDraft,
  employmentTypes,
  toInvitation,
  validateStep,
  type DraftErrors,
  type MemberDraft,
  type Step,
} from './memberDraft.ts'

/**
 * Add New User form state: the draft, the current step and its field errors.
 * Each step is validated before moving on; nothing is sent until Review.
 */
export function useAddMemberDraft(
  initial: Partial<MemberDraft>,
  onSubmit: (request: MemberInvitationCreate) => Promise<string | null>,
  onSent: () => void,
) {
  const [draft, setDraft] = useState(() => emptyDraft(initial))
  const [step, setStep] = useState<Step>(0)
  const [errors, setErrors] = useState<DraftErrors>({})
  const [serverError, setServerError] = useState<string | null>(null)

  function update<K extends keyof MemberDraft>(field: K, value: MemberDraft[K]) {
    setDraft((current) => {
      const next = { ...current, [field]: value }
      // Staff cannot be visiting or guest; fall back to a type the role allows.
      if (field === 'role' && !(next.employment_type in employmentTypes(next.role))) {
        next.employment_type = 'permanent'
      }
      // Employment usually starts on the joining date; prefill until changed.
      if (field === 'joining_date' && current.employment_start_date === current.joining_date) {
        next.employment_start_date = value as string
      }
      if (field === 'department_id') {
        next.additional_department_ids = current.additional_department_ids.filter((id) => id !== value)
      }
      return next
    })
    setErrors((current) => ({ ...current, [field]: undefined }))
  }

  function next() {
    const found = validateStep(step, draft)
    setErrors(found)
    if (Object.values(found).some(Boolean)) return
    setServerError(null)
    setStep((current) => Math.min(current + 1, 2) as Step)
  }

  function back() {
    setErrors({})
    setServerError(null)
    setStep((current) => Math.max(current - 1, 0) as Step)
  }

  async function send() {
    setServerError(null)
    const failure = await onSubmit(toInvitation(draft))
    if (failure) setServerError(failure)
    else onSent()
  }

  return { draft, step, errors, serverError, update, next, back, send }
}

export type AddMemberDraftModel = ReturnType<typeof useAddMemberDraft>
