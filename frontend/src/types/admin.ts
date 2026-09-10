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
// Dashboard
// ============================================================================

export interface DashboardSummary {
  counts: {
    knowledge_sources: number
    documents: number
    faqs: number
    notices: number
    students: number
    student_results: number
    test_results: number
    attendance_records: number
  }
  recent_audit: AuditLogEntry[]
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
