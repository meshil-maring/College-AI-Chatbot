/**
 * Phase 6.16 — Student experience dashboard types.
 *
 * Typed mirror of the EXISTING student-facing backend contracts. Every field
 * below was verified against the backend schema before writing; no field is
 * guessed and no dashboard-only field is invented.
 *
 *   GET /api/v1/students/me/academic-profile   (app/schemas/student_profile.py)
 *   GET /api/v1/students/me/attendance/summary (app/schemas/student_attendance.py)
 *   GET /api/v1/students/me/results/summary    (app/schemas/student_results.py)
 *   GET /api/v1/students/me/test-results/summary (app/schemas/student_results.py)
 *   GET /api/v1/students/me/notices            (app/schemas/student_notices.py)
 *   GET /api/v1/students/me/resources          (app/schemas/student_resources.py)
 *
 * Data handling rules honoured by these types:
 *  - no internal database identifiers other than the stable list keys the
 *    backend contract already exposes (`notice_id`, `resource_id`), which the
 *    UI uses as React keys only and NEVER renders;
 *  - no tenant identifiers, no tokens, no storage keys, no signed URLs.
 */

// ============================================================================
// Academic profile (identity + academic context)
// ============================================================================

/** Response of GET /api/v1/students/me/academic-profile (Phase 6.14.1). */
export interface StudentAcademicProfile {
  student_number: string | null
  register_number: string | null
  university_roll_number: string | null
  email: string | null
  institution_name: string | null
  institution_code: string | null
  program_name: string | null
  program_code: string | null
  academic_year_name: string | null
  academic_year_code: string | null
  current_semester_name: string | null
  current_semester_code: string | null
  approval_status: string | null
  status: string | null
}

// ============================================================================
// Attendance (Phase 6.14.2)
// ============================================================================

/** Server-computed attendance summary. The percentage is authoritative. */
export interface StudentAttendanceSummary {
  records_available: boolean
  total_classes: number
  present_classes: number
  absent_classes: number
  late_classes: number
  excused_classes: number
  attendance_percentage: number | null
}

/** One student-safe attendance day. */
export interface StudentAttendanceRecord {
  date: string | null
  status: string | null
  notes: string | null
}

/** Response of GET /api/v1/students/me/attendance/summary. */
export interface StudentOwnAttendance {
  summary: StudentAttendanceSummary
  records: StudentAttendanceRecord[]
}

// ============================================================================
// Results (Phase 6.14.3)
// ============================================================================

/** One published academic result summary. */
export interface StudentAcademicResultRecord {
  result_type: string | null
  total_credits_earned: number | null
  total_credits_max: number | null
  sgpa: number | null
  cgpa: number | null
  status: string | null
  issued_at: string | null
}

/** One published per-test score. */
export interface StudentTestResultRecord {
  test_name: string | null
  test_type: string | null
  course_code: string | null
  course_name: string | null
  max_marks: number | null
  scored_marks: number | null
  percentage: number | null
  letter_grade: string | null
  conducted_at: string | null
}

/** Academic-result summary (counts only — no invented aggregates). */
export interface StudentOwnResultsSummary {
  records_available: boolean
  total_results: number
}

/** Test-result summary (counts only — no invented aggregates). */
export interface StudentOwnTestResultsSummary {
  records_available: boolean
  total_results: number
}

/** Response of GET /api/v1/students/me/results/summary. */
export interface StudentOwnResults {
  summary: StudentOwnResultsSummary
  records: StudentAcademicResultRecord[]
}

/** Response of GET /api/v1/students/me/test-results/summary. */
export interface StudentOwnTestResults {
  summary: StudentOwnTestResultsSummary
  records: StudentTestResultRecord[]
}

// ============================================================================
// Notices (Phase 6.16)
// ============================================================================

/** One published notice for the authenticated student's institution. */
export interface StudentNotice {
  /** Stable list key only — never rendered. */
  notice_id: string
  title: string
  content: string
  category: string
  priority: string
  is_pinned: boolean
  published_at: string | null
  expires_at: string | null
}

/** Response of GET /api/v1/students/me/notices. */
export interface StudentNoticeList {
  items: StudentNotice[]
  total: number
}

// ============================================================================
// Learning resources (Phase 6.16)
// ============================================================================

/** One published learning resource for the student's own institution. */
export interface StudentResource {
  /** Stable list key only — never rendered. */
  resource_id: string
  title: string
  description: string | null
  source_type: string
  effective_from: string | null
  effective_until: string | null
}

/** Response of GET /api/v1/students/me/resources. */
export interface StudentResourceList {
  items: StudentResource[]
  total: number
}
