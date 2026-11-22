import type {
  FacultyEmploymentType,
  MemberInvitationCreate,
  MembershipRole,
  StaffCategory,
  StaffEmploymentType,
} from '../../../../../types/admin.ts'

/** The three steps of Add New User: common details, role details, review. */
export const STEPS = ['Basic details', 'Role details', 'Review'] as const
export type Step = 0 | 1 | 2

/** Everything typed into the form, as strings until it is sent. */
export interface MemberDraft {
  full_name: string
  email: string
  phone: string
  employee_id: string
  designation: string
  joining_date: string
  role: MembershipRole
  department_id: string
  additional_department_ids: string[]
  employment_type: string
  employment_start_date: string
  contract_end_date: string
  qualification: string
  specialization: string
  experience_years: string
  staff_category: string
  responsibilities: string[]
}

export type DraftField = keyof MemberDraft
export type DraftErrors = Partial<Record<DraftField, string>>

/** What the shared form fields need: the draft, its errors and a setter. */
export interface DraftFieldsModel {
  draft: MemberDraft
  errors: DraftErrors
  update: <K extends DraftField>(field: K, value: MemberDraft[K]) => void
}

export const FACULTY_EMPLOYMENT: Record<FacultyEmploymentType, string> = {
  permanent: 'Permanent',
  temporary: 'Temporary',
  contractual: 'Contractual',
  visiting: 'Visiting Faculty',
  guest: 'Guest Lecturer',
}

export const STAFF_EMPLOYMENT: Record<StaffEmploymentType, string> = {
  permanent: 'Permanent',
  temporary: 'Temporary',
  contractual: 'Contractual',
}

export const STAFF_CATEGORIES: Record<StaffCategory, string> = {
  office_administration: 'Office Administration',
  accounts_finance: 'Accounts and Finance',
  library: 'Library Staff',
  it_support: 'IT Support',
  laboratory: 'Laboratory Staff',
  hostel_administration: 'Hostel Administration',
  examination_office: 'Examination Office',
  other: 'Other Staff',
}

export function emptyDraft(initial: Partial<MemberDraft> = {}): MemberDraft {
  return {
    full_name: '',
    email: '',
    phone: '',
    employee_id: '',
    designation: '',
    joining_date: '',
    role: 'faculty',
    department_id: '',
    additional_department_ids: [],
    employment_type: 'permanent',
    employment_start_date: '',
    contract_end_date: '',
    qualification: '',
    specialization: '',
    experience_years: '',
    staff_category: '',
    responsibilities: [],
    // Known details only: an undefined value must not replace a default.
    ...Object.fromEntries(Object.entries(initial).filter(([, value]) => value !== undefined)),
  }
}

/** Employment types allowed for the role; Staff cannot be visiting or guest. */
export function employmentTypes(role: MembershipRole): Record<string, string> {
  return role === 'faculty' ? FACULTY_EMPLOYMENT : STAFF_EMPLOYMENT
}

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const EMPLOYEE_ID = /^[A-Za-z0-9][A-Za-z0-9._/-]{0,39}$/
export const PHONE = /^\+?[0-9][0-9 ()-]{4,30}$/
export const clean = (value: string) => value.split(/\s+/).filter(Boolean).join(' ')

/** Field errors for one step; the same rules the server applies. */
export function validateStep(step: Step, draft: MemberDraft): DraftErrors {
  const errors: DraftErrors = {}
  if (step === 0) {
    if (!clean(draft.full_name)) errors.full_name = 'Enter their name.'
    if (!EMAIL.test(draft.email.trim())) errors.email = 'Enter a valid email address.'
    if (draft.phone.trim() && !PHONE.test(clean(draft.phone))) errors.phone = 'Enter a valid phone number.'
    if (!EMPLOYEE_ID.test(draft.employee_id.trim()))
      errors.employee_id = 'Use up to 40 letters, numbers and . _ / - (start with a letter or number).'
    if (!clean(draft.designation)) errors.designation = 'Enter the designation.'
    if (!draft.joining_date) errors.joining_date = 'Choose the joining date.'
  }
  if (step === 1) {
    if (!draft.department_id) errors.department_id = 'Choose the primary department.'
    if (!(draft.employment_type in employmentTypes(draft.role))) errors.employment_type = 'Choose the employment type.'
    if (!draft.employment_start_date) errors.employment_start_date = 'Choose the employment start date.'
    if (draft.employment_type !== 'permanent' && !draft.contract_end_date)
      errors.contract_end_date = 'Enter the contract end date for non-permanent employment.'
    else if (draft.contract_end_date && draft.contract_end_date < draft.employment_start_date)
      errors.contract_end_date = 'The contract cannot end before employment starts.'
    if (draft.role === 'faculty' && draft.experience_years) {
      const years = Number(draft.experience_years)
      if (!Number.isFinite(years) || years < 0 || years > 70) errors.experience_years = 'Enter 0 to 70 years.'
    }
    if (draft.role === 'staff') {
      if (!(draft.staff_category in STAFF_CATEGORIES)) errors.staff_category = 'Choose the staff category.'
      if (draft.responsibilities.length === 0) errors.responsibilities = 'Add at least one responsibility.'
    }
  }
  return errors
}

/** The invitation request: common profile plus only the selected role's details. */
export function toInvitation(draft: MemberDraft): MemberInvitationCreate {
  const optional = (value: string) => clean(value) || null
  const employment = {
    employment_start_date: draft.employment_start_date,
    contract_end_date: draft.employment_type === 'permanent' ? null : draft.contract_end_date || null,
  }
  return {
    full_name: clean(draft.full_name),
    email: draft.email.trim().toLowerCase(),
    role: draft.role,
    department_id: draft.department_id,
    additional_department_ids: draft.additional_department_ids.filter((id) => id !== draft.department_id),
    profile: {
      common: {
        employee_id: draft.employee_id.trim(),
        phone: optional(draft.phone),
        designation: clean(draft.designation),
        joining_date: draft.joining_date,
      },
      ...(draft.role === 'faculty'
        ? {
            faculty: {
              ...employment,
              employment_type: draft.employment_type as FacultyEmploymentType,
              qualification: optional(draft.qualification),
              specialization: optional(draft.specialization),
              experience_years: draft.experience_years ? Number(draft.experience_years) : null,
            },
          }
        : {
            staff: {
              ...employment,
              employment_type: draft.employment_type as StaffEmploymentType,
              staff_category: draft.staff_category as StaffCategory,
              responsibilities: draft.responsibilities,
            },
          }),
    },
  }
}
