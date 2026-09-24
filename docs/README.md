# Documentation index

Phase documentation, validation evidence and schema snapshots live here. These are **historical
artifacts**: each file records what was true when its phase was locked or validated.

| Directory | Contents |
| --- | --- |
| `locks/` | Phase lock records (`PHASE_*_LOCK.md`, `FINAL_DEMO_LOCK.md`): frozen scope and evidence per phase |
| `status/` | Phase status/scope reports and review prompts (`PHASE_*_STATUS.md`, `PHASE_*_SCOPE_REPORT.md`, other `PHASE_*` phase reports, `FINAL_DEMO_STATUS.md`) |
| `reports/` | Physical-validation and implementation reports (Markdown + HTML) |
| `evidence/` | Raw JSON evidence captured during validation runs (latency/behaviour baselines, physical validation results, OpenAPI dump) |
| `schema/` | `schemaV2_export.sql` — exported database schema snapshot |
| `mcp/` | Postman MCP guide (`postman_mcp_readme.md`) and its captured documentation page |

## Notes

- Database migrations are **not** stored here; they live in `supabase/migrations/`.
- Lock files are append-only records and should not be edited after the fact.
- Reports and status files quote the commands used at the time, e.g. `cd backend` followed by
  `python test_physical_phase_4_2.py`. Those scripts have since moved into `backend/scripts/`, so use
  the current paths documented in `backend/scripts/README.md`.
- The evidence JSON in `evidence/` is referenced by the lock and report files; keep names stable.