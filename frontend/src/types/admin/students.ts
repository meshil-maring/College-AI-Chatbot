// ============================================================================
// Students
// ============================================================================

export interface Student {
  student_id: string
  user_id: string
  institution_id: string
  student_number: string
  program_id: string | null
  academic_year_id: string | null
  enrollment_date: string | null
  expected_graduation_date: string | null
  status: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface StudentCreate {
  user_id: string
  institution_id: string
  student_number: string
  program_id?: string | null
  academic_year_id?: string | null
  enrollment_date?: string | null
  expected_graduation_date?: string | null
  status?: string
}

export interface StudentUpdate {
  student_number?: string | null
  program_id?: string | null
  academic_year_id?: string | null
  enrollment_date?: string | null
  expected_graduation_date?: string | null
  status?: string | null
  is_active?: boolean | null
}

// ============================================================================
// Results
// ============================================================================

export interface StudentResult {
  student_result_id: string
  student_id: string
  academic_year_id: string | null
  semester_id: string | null
  program_id: string | null
  result_type: string
  total_credits_earned: number | null
  total_credits_max: number | null
  sgpa: number | null
  cgpa: number | null
  status: string
  issued_at: string | null
}

export interface ResultCreate {
  student_id: string
  academic_year_id?: string | null
  semester_id?: string | null
  program_id?: string | null
  result_type?: string
  total_credits_earned?: number | null
  total_credits_max?: number | null
  sgpa?: number | null
  cgpa?: number | null
  status?: string
}

export interface ResultUpdate {
  result_type?: string | null
  total_credits_earned?: number | null
  total_credits_max?: number | null
  sgpa?: number | null
  cgpa?: number | null
  status?: string | null
}

// ============================================================================
// Test results
// ============================================================================

export interface TestResult {
  test_result_id: string
  student_id: string
  course_id: string | null
  section_id: string | null
  academic_year_id: string | null
  semester_id: string | null
  test_name: string
  test_type: string | null
  max_marks: number | null
  scored_marks: number | null
  percentage: number | null
  letter_grade: string | null
  conducted_at: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface TestResultCreate {
  student_id: string
  course_id?: string | null
  section_id?: string | null
  academic_year_id?: string | null
  semester_id?: string | null
  test_name: string
  test_type?: string | null
  max_marks?: number | null
  scored_marks?: number | null
  percentage?: number | null
  letter_grade?: string | null
  conducted_at?: string | null
  status?: string
}

export interface TestResultUpdate {
  test_name?: string | null
  test_type?: string | null
  max_marks?: number | null
  scored_marks?: number | null
  percentage?: number | null
  letter_grade?: string | null
  conducted_at?: string | null
  status?: string | null
}

// ============================================================================
// Attendance
// ============================================================================

export interface AttendanceRecord {
  student_attendance_id: string
  student_id: string
  section_id: string | null
  academic_year_id: string | null
  semester_id: string | null
  date: string
  status: string
  notes: string | null
  created_at: string
}

export interface AttendanceCreate {
  student_id: string
  section_id?: string | null
  academic_year_id?: string | null
  semester_id?: string | null
  date: string
  status: string
  notes?: string | null
}

export interface AttendanceUpdate {
  section_id?: string | null
  date?: string | null
  status?: string | null
  notes?: string | null
}

/**
 * Phase 6.19 — mirror of the backend CSV upload result contract
 * (backend/app/services/admin_academics.py `CsvUploadResult` / `CsvRowError`).
 * The endpoint is POST /api/v1/admin/results/csv-upload.
 */
export interface CsvRowError {
  row: number
  student_number: string | null
  errors: string[]
}

export interface CsvUploadResult {
  total_rows: number
  inserted_count: number
  failed_count: number
  row_errors: CsvRowError[]
}

// ============================================================================
// Student self-service
// ============================================================================

export interface StudentProfile {
  student_id: string
  user_id: string
  institution_id: string
  student_number: string
  program_id: string | null
  academic_year_id: string | null
  enrollment_date: string | null
  expected_graduation_date: string | null
  status: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// ============================================================================
// Student approval queue (Phase 6.4 backend contract; Phase 6.18 staff UI)
// ============================================================================

/**
 * Phase 6.18 — one row of the tenant-scoped student approval queue
 * (GET /api/v1/admin/students/pending; backend `require_roles("admin","staff")`
 * with the tenant resolved server-side). Mirrors the backend
 * `STUDENT_APPROVAL_COLUMNS` projection exactly. Internal identifiers
 * (`student_id`, `user_id`, `institution_id`) are present in the payload but
 * must NEVER be rendered by any UI consumer (data minimization).
 */
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
  enrollment_date: string | null
  created_at: string
  updated_at: string
}
