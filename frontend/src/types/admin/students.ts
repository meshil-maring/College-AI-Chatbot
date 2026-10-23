/** Account approval row; internal keys are used for decisions and never displayed. */
export interface PendingStudent {
  student_id: string
  user_id: string
  institution_id: string
  student_number: string
  email: string | null
  register_number: string | null
  university_roll_number: string | null
  approval_status: string
  status: string
  is_active: boolean
  created_at: string
  updated_at: string
}
