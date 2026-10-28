# Documentation index

Reference documentation, phase records, validation evidence, and schema snapshots live here.
Phase records are **historical artifacts**: each records what was true when its phase was locked
or validated. The [RBAC reading guide](rbac/README.md) organizes the review draft by role so future
tasks can load only the shared rules and relevant user section.

| Directory | Contents |
| --- | --- |
| `architecture/` | Implementation records and explicitly labeled design drafts. See [Academic Setup](architecture/academic-setup/README.md) for its implemented architecture, and the [shared learning resources and AI chatbot draft](architecture/ai-chatbot/README.md) for proposed UI, permissions and workflows. |
| `rbac/` | Review-only RBAC documentation: shared rules, role-specific access, permission catalog, workflows, and verification gaps. Start with its [reading guide](rbac/README.md). |
| `locks/` | Phase lock records (`PHASE_*_LOCK.md`, `FINAL_DEMO_LOCK.md`): frozen scope and evidence per phase |
| `status/` | Phase status/scope reports and review prompts (`PHASE_*_STATUS.md`, `PHASE_*_SCOPE_REPORT.md`, other `PHASE_*` phase reports, `FINAL_DEMO_STATUS.md`) |
| `reports/` | Physical-validation and implementation reports (Markdown + HTML) |
| `evidence/` | Raw JSON evidence captured during validation runs (latency/behaviour baselines, physical validation results, OpenAPI dump) |
| `schema/` | `schemaV2_export.sql` — exported database schema snapshot |
| `reports/` | Validation/implementation reports plus the root-level security audit reports (`M1_PREFLIGHT_AUDIT_REPORT.md`, `SECURITY_REMEDIATION_PLANNING_REPORT.md`) |
| `retirements/` | Approved feature removals. See the [Academic Setup removal record](retirements/academic-setup/README.md). |
| `reviews/` | Independent review packages (e.g. `student_enrollment_final_2026-10-11/`) |
| `security/` | Security audit records |
| `mcp/` | Postman MCP guide (`postman_mcp_readme.md`) and its captured documentation page |

## Notes

- Database migrations are **not** stored here; they live in `supabase/migrations/`.
- Lock files are append-only records and should not be edited after the fact.
- Reports and status files quote the commands used at the time, e.g. `cd backend` followed by
  `python test_physical_phase_4_2.py`. Those scripts have since moved into `backend/scripts/`, so use
  the current paths documented in `backend/scripts/README.md`.
- The evidence JSON in `evidence/` is referenced by the lock and report files; keep names stable.
