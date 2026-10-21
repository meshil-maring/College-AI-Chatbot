// ============================================================================
// Dashboard (Phase 7.21 — GET /api/v1/admin/dashboard)
// ============================================================================

/** Typed mirror of `DashboardInstitution` (backend/app/schemas/admin/admin_dashboard.py). */
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
