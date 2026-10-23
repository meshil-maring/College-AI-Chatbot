/** Identity and published information returned for the authenticated student. */
export interface StudentIdentityProfile {
  student_number: string | null
  register_number: string | null
  university_roll_number: string | null
  email: string | null
  institution_name: string | null
  institution_code: string | null
  approval_status: string | null
  status: string | null
}
export interface StudentNotice {
  notice_id: string
  title: string
  content: string
  category: string
  priority: string
  is_pinned: boolean
  published_at: string | null
  expires_at: string | null
}
export interface StudentNoticeList {
  items: StudentNotice[]
  total: number
}
export interface StudentResource {
  resource_id: string
  title: string
  description: string | null
  source_type: string
  effective_from: string | null
  effective_until: string | null
}
export interface StudentResourceList {
  items: StudentResource[]
  total: number
}
