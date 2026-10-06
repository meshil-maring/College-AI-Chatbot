/**
 * Phase Admin-4 — Admin module frontend types.
 *
 * Typed mirror of the backend admin API contracts (backend/app/schemas/admin.py
 * and backend/app/api/admin.py). Only fields the backend actually returns are
 * declared. These types are consumed by adminApi.ts and the admin feature
 * components.
 */

// ============================================================================
// Knowledge sources
// ============================================================================

export interface KnowledgeSource {
  knowledge_source_id: string
  institution_id: string
  source_type: string
  title: string
  description: string | null
  authority_level: string
  lifecycle_status: string
  effective_from: string | null
  effective_until: string | null
  created_at: string
  updated_at: string
}

export interface KnowledgeSourceCreate {
  institution_id: string
  source_type: string
  title: string
  description?: string | null
  authority_level?: string
  lifecycle_status?: string
  effective_from?: string | null
  effective_until?: string | null
}

export interface KnowledgeSourceUpdate {
  title?: string | null
  description?: string | null
  authority_level?: string | null
  lifecycle_status?: string | null
  effective_from?: string | null
  effective_until?: string | null
}

// ============================================================================
// Documents and versions
// ============================================================================

export interface DocumentVersion {
  document_version_id: string
  document_id: string
  version_number: number
  version_label: string | null
  original_filename: string
  file_type: string
  mime_type: string | null
  file_size_bytes: number | null
  storage_bucket: string
  storage_object_key: string
  file_checksum: string | null
  lifecycle_status: string
  supersedes_version_id: string | null
  created_by_user_id: string
  created_at: string
  updated_at: string
}

export interface DocumentWithVersions {
  document_id: string
  knowledge_source_id: string
  created_at: string
  updated_at: string
  versions: DocumentVersion[]
}

// ============================================================================
// FAQs
// ============================================================================

export interface Faq {
  faq_id: string
  institution_id: string | null
  category: string
  question: string
  answer: string
  display_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface FaqCreate {
  institution_id?: string | null
  category?: string
  question: string
  answer: string
  display_order?: number
  is_active?: boolean
}

export interface FaqUpdate {
  category?: string | null
  question?: string | null
  answer?: string | null
  display_order?: number | null
  is_active?: boolean | null
}

// ============================================================================
// Notices
// ============================================================================

export interface Notice {
  notice_id: string
  institution_id: string | null
  title: string
  content: string
  category: string
  priority: string
  is_active: boolean
  is_pinned: boolean
  published_at: string | null
  expires_at: string | null
  created_by: string | null
  created_at: string
  updated_at: string
}

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

// ============================================================================
// Dashboard (Phase 7.21 — GET /api/v1/admin/dashboard)
// ============================================================================

/** Typed mirror of `DashboardInstitution` (backend/app/schemas/admin_dashboard.py). */
export interface DashboardInstitution {
  name: string
  code: string
  status: string
}

/** Typed mirror of `DashboardStudents`. */
export interface DashboardStudents {
  total: number
  pending_approvals: number
  approved: number
  active: number
}

/**
 * Typed mirror of `DashboardKnowledge`.
 * `failed_processing_runs` is `null` when the metric is not resolvable from the
 * current schema; the UI renders it as "Unavailable" and never as `0`.
 */
export interface DashboardKnowledge {
  sources_total: number
  sources_active: number
  documents_total: number
  failed_processing_runs: number | null
}

/** Typed mirror of `DashboardRecentNotice` — display fields only, no notice_id. */
export interface DashboardRecentNotice {
  title: string
  category: string
  priority: string
  published_at: string | null
}

/** Typed mirror of `DashboardCommunication`. */
export interface DashboardCommunication {
  active_faqs: number
  active_notices: number
  recent_notices: DashboardRecentNotice[]
}

/** Typed mirror of `DashboardAcademics`. */
export interface DashboardAcademics {
  attendance_records: number
  test_results: number
  results: number
}

/**
 * A navigation affordance for an EXISTING admin screen. `view` is one of the
 * `AdminView` keys in `adminNavigation.ts`; the backend never introduces a new
 * screen, it only names an existing one.
 */
export interface DashboardQuickAction {
  view: string
  label: string
  description: string
}

/**
 * Phase 7.21 — the complete institution-scoped dashboard payload.
 *
 * Security: this contract carries no internal identifiers (no institution_id,
 * user_id, auth_user_id, audit_id, notice_id) and no audit rows. The previous
 * `{ counts, recent_audit }` shape is intentionally gone: `recent_audit`
 * exposed raw `admin_audit_log` rows (actor ids, record_data, ip_address,
 * user_agent) which are internals the dashboard must not surface.
 */
export interface DashboardSummary {
  institution: DashboardInstitution
  students: DashboardStudents
  knowledge: DashboardKnowledge
  communication: DashboardCommunication
  academics: DashboardAcademics
  quick_actions: DashboardQuickAction[]
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
// Audit log
// ============================================================================

export interface AuditLogEntry {
  audit_id: string
  actor_user_id: string
  action: string
  table_name: string | null
  record_id: string | null
  record_data: Record<string, unknown> | null
  ip_address: string | null
  user_agent: string | null
  status: string
  performed_at: string
}

// ============================================================================
// Admin identity
// ============================================================================

export interface AdminIdentity {
  user_id: string
  auth_user_id: string
  email: string | null
  roles: string[]
  is_admin: boolean
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

export interface NoticeCreate {
  institution_id?: string | null
  title: string
  content: string
  category?: string
  priority?: string
  is_active?: boolean
  is_pinned?: boolean
  published_at?: string | null
  expires_at?: string | null
}

export interface NoticeUpdate {
  title?: string | null
  content?: string | null
  category?: string | null
  priority?: string | null
  is_active?: boolean | null
  is_pinned?: boolean | null
  published_at?: string | null
  expires_at?: string | null
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

// ============================================================================
// Staff / Faculty onboarding and roster (Phase 7.23)
// ============================================================================

export type MembershipRole = 'staff' | 'faculty'
export type MembershipRequestStatus = 'pending' | 'approved' | 'rejected'

export interface MembershipRequest {
  request_id: string
  full_name: string
  email: string
  requested_role: MembershipRole
  status: MembershipRequestStatus
  created_at: string
}

export interface MembershipRequestList {
  requests: MembershipRequest[]
  total: number
}

export interface MembershipDecisionResult {
  request_id: string
  status: 'approved' | 'rejected'
  already_applied: boolean
  message: string
}

export interface MembershipRosterEntry {
  user_id: string
  name: string
  email: string
  role: MembershipRole
  status: string
  created_at: string | null
  updated_at: string | null
}

export interface MembershipRoster {
  members: MembershipRosterEntry[]
  total: number
}

export interface MembershipLifecycleResult {
  user_id: string
  status: 'active' | 'deactivated'
  already_applied: boolean
  message: string
}
