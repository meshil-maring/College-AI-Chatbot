import type { AdminProfile } from '../../../../types/admin/administrators.ts'
import { EMPLOYEE_ID, PHONE, clean } from '../invitations/add-member/memberDraft.ts'

/** Form values for an administrator's employee details. */
export interface AdminProfileDraft {
  employee_id: string
  phone: string
  designation: string
  joining_date: string
}
export type AdminProfileErrors = Partial<Record<keyof AdminProfileDraft, string>>

export function profileDraft(profile: AdminProfile | null): AdminProfileDraft {
  return {
    employee_id: profile?.employee_id ?? '',
    phone: profile?.phone ?? '',
    designation: profile?.designation ?? '',
    joining_date: profile?.joining_date?.slice(0, 10) ?? '',
  }
}

/** The same rules as Staff and Faculty, which the server repeats. */
export function validateProfile(draft: AdminProfileDraft): AdminProfileErrors {
  const errors: AdminProfileErrors = {}
  if (!EMPLOYEE_ID.test(draft.employee_id.trim()))
    errors.employee_id = 'Use up to 40 letters, numbers and . _ / - (start with a letter or number).'
  if (draft.phone.trim() && !PHONE.test(clean(draft.phone))) errors.phone = 'Enter a valid phone number.'
  if (!clean(draft.designation)) errors.designation = 'Enter the designation.'
  if (!draft.joining_date) errors.joining_date = 'Choose the joining date.'
  return errors
}

export function toProfile(draft: AdminProfileDraft): AdminProfile {
  return {
    employee_id: draft.employee_id.trim(),
    phone: clean(draft.phone) || null,
    designation: clean(draft.designation),
    joining_date: draft.joining_date,
  }
}

/** Short line for lists, or null when the profile is missing. */
export function profileSummary(profile: AdminProfile | null) {
  return profile ? `${profile.designation} · ${profile.employee_id}` : null
}
