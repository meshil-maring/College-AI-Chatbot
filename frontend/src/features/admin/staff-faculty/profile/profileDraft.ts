import type { MembershipRosterEntry } from '../../../../types/admin.ts'
import type { MemberProfileView } from '../../../../types/admin/memberProfiles.ts'
import { emptyDraft, type MemberDraft } from '../invitations/add-member/memberDraft.ts'

/**
 * The Add member draft filled from a member's saved profile, so editing uses
 * the same fields and validation as inviting. Name, email and role are shown
 * but changed elsewhere (sign-in identity and the roster's role picker).
 */
export function profileToDraft(member: MembershipRosterEntry, profile: MemberProfileView | undefined): MemberDraft {
  const detail = member.role === 'faculty' ? profile?.faculty : profile?.staff
  const faculty = profile?.faculty
  return emptyDraft({
    full_name: member.name || member.email,
    email: member.email,
    role: member.role,
    phone: profile?.common?.phone ?? '',
    employee_id: profile?.common?.employee_id ?? '',
    designation: profile?.common?.designation ?? '',
    joining_date: profile?.common?.joining_date ?? '',
    department_id: profile?.primary_department?.department_id ?? member.department_id ?? '',
    additional_department_ids: (profile?.additional_departments ?? []).map((item) => item.department_id),
    employment_type: detail?.employment_type ?? 'permanent',
    employment_start_date: detail?.employment_start_date ?? profile?.common?.joining_date ?? '',
    contract_end_date: detail?.contract_end_date ?? '',
    qualification: member.role === 'faculty' ? (faculty?.qualification ?? '') : '',
    specialization: member.role === 'faculty' ? (faculty?.specialization ?? '') : '',
    experience_years:
      member.role === 'faculty' && faculty?.experience_years != null ? String(faculty.experience_years) : '',
    staff_category: profile?.staff?.staff_category ?? '',
    responsibilities: profile?.staff?.responsibilities ?? [],
  })
}
