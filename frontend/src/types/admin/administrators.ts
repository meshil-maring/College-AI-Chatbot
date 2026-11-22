/** Institution administrators and the Owner, who alone manages them. */

/** Areas the Owner can allow an administrator. `null` means full access. */
export type AdminAccessArea =
  'staff_faculty' | 'students' | 'academic_setup' | 'content' | 'staff_permissions' | 'settings_audit'

/** Shared employee fields of an administrator. */
export interface AdminProfile {
  employee_id: string
  phone: string | null
  designation: string
  joining_date: string
}

export interface InstitutionAdmin {
  user_id: string
  name: string
  email: string
  status: string
  assigned_at: string | null
  is_owner: boolean
  access_areas: AdminAccessArea[] | null
  /** `null` until the Owner or the administrator fills it in. */
  profile: AdminProfile | null
}

export interface AdminInvitation {
  invitation_id: string
  email: string
  full_name: string | null
  expires_at: string | null
  created_at: string | null
  email_delivery_status: string | null
  access_areas: AdminAccessArea[] | null
  profile: AdminProfile | null
}

export interface InstitutionAdminList {
  owner_user_id: string | null
  /** Whether the signed-in administrator is the Owner. */
  viewer_is_owner: boolean
  /** The signed-in administrator, who may edit their own profile. */
  viewer_user_id: string | null
  administrators: InstitutionAdmin[]
  invitations: AdminInvitation[]
  /** Every area, in display order. */
  access_area_options: AdminAccessArea[]
}

export interface InstitutionAdminResult {
  message: string
  already_applied: boolean
}
