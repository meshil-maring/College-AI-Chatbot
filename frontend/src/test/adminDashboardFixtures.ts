/**
 * Phase 7.21 — shared AdminDashboard test fixtures.
 *
 * Every dashboard test builds its payload from this ONE typed factory so the
 * fixtures cannot drift from the real `DashboardSummary` contract. The zero
 * factory models a brand-new institution; `buildDashboardSummary` allows
 * overriding any section for metric-rendering tests.
 */

import type { DashboardSummary } from '../types/admin.ts'

/** A brand-new institution: every metric zero, no notices, no quick actions. */
export function emptyDashboardSummary(): DashboardSummary {
  return {
    institution: { name: 'Fresh University', code: 'FRESH', status: 'active' },
    students: { total: 0, pending_approvals: 0, approved: 0, active: 0 },
    knowledge: {
      sources_total: 0,
      sources_active: 0,
      documents_total: 0,
      // Unresolvable from the current schema: null, never a fabricated 0.
      failed_processing_runs: null,
    },
    communication: { active_faqs: 0, active_notices: 0, recent_notices: [] },
    academics: { attendance_records: 0, test_results: 0, results: 0 },
    quick_actions: [],
  }
}

/** A populated institution with the production quick-action set. */
export function buildDashboardSummary(
  overrides: Partial<DashboardSummary> = {},
): DashboardSummary {
  return {
    ...emptyDashboardSummary(),
    institution: {
      name: 'Alpha University',
      code: 'ALPHA',
      status: 'active',
    },
    students: { total: 7, pending_approvals: 2, approved: 5, active: 6 },
    knowledge: {
      sources_total: 2,
      sources_active: 2,
      documents_total: 5,
      failed_processing_runs: null,
    },
    communication: {
      active_faqs: 3,
      active_notices: 4,
      recent_notices: [
        {
          title: 'Exam schedule published',
          category: 'academic',
          priority: 'high',
          published_at: '2026-01-01T00:00:00Z',
        },
      ],
    },
    academics: { attendance_records: 11, test_results: 6, results: 9 },
    quick_actions: [
      {
        view: 'approvals',
        label: 'Approve Student',
        description: 'Review the pending student approval queue.',
      },
      {
        view: 'notices',
        label: 'Create Notice',
        description: 'Publish a notice for students to see.',
      },
    ],
    ...overrides,
  }
}
