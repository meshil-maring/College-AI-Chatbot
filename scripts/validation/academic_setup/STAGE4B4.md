# Stage 4B-4 remediation report

Historical status: **independent review returned NOT READY; execution remains disabled**.
Stage 4B-5 remediation is documented in [STAGE4B5.md](STAGE4B5.md).
The verification counts below describe Stage 4B-4, not the later remediated source.
The Stage 4B-3 findings supplied in the request are the complete review baseline.
No Docker command, container operation, database connection, SQL or migration was
executed. The database schema remains unapplied. There is no hosted fallback.

## Changes

- Identity now requires complete immutable image and engine IDs, absolute local
  executable path/hash, client/server versions, complete image Config fingerprint,
  bootstrap command fingerprint and non-root UID/GID. Future runtime checks verify
  exec/PID 1 identities and postgres/initdb versions. Unknown evidence fails closed.
- Snapshots include trigger definitions/enabled state, policies, indexes, forced
  RLS, ownership, table/column/function/schema/default ACLs and sequence definitions,
  owners and ACLs. Correction: Stage 4B-4 mutation probes did not exercise existing
  trigger enabled state, forced RLS or sequence definition/owner/ACL changes.
- A real unexpected preserved-table FK must produce the original decommission
  prerequisite refusal (exact P0001 message), followed by full snapshot equality.
  The separate late-transaction P4001 rollback lane remains intact.
- Synthetic SQL covers two tenants, foreign actors/records/all parent references,
  delegated-only permissions, split role provenance, inactive principals and
  invalid scope/authority combinations. Lifecycle checks include active/inactive
  uniqueness across all seven entities, ancestor refusal, bottom-up deactivation,
  parent-first reactivation and retained assignment identity.
- Four synchronized paired-session lanes observe real blocking or another tenant's
  committed progress. They check duplicate commits, parent/child races, tenant
  independence and lock release after rollback. Correction: tenant B creation and
  parent-deactivation audits lacked exact identity/count/transition assertions.
- Audit rollback checks create/update/deactivate operations through foundation,
  structure and section APIs, requiring the exact injected constraint name.
  Catalog privilege probes cover column grants, REFERENCES/TRIGGER/MAINTAIN, helper execution,
  ownership, SECURITY DEFINER and exact safe search_path configuration.
  Correction: these did not switch database roles to exercise actual denials.
- Readiness checks the monotonic deadline before/after blocking operations, including
  late successful readiness and executable verification. SQL rechecks its separate
  budget immediately before submission. Cleanup closes only after successful exact
  full-ID absence confirmation on the revalidated fixed engine.
  Correction: readiness retried only code 1, inspections did not receive the
  remaining budget, and SQL lacked a completion-time deadline check.

The review also found that retained-state comparison accepted arbitrary added
catalog objects; Stage 4B-4 had no explicit approved inventory for additions.

The fixed endpoint, image reference, ID-only creation, --pull=never, network none,
no published ports/binds/persistent volumes, 512 MiB tmpfs, original 49 migration
files/order and individual transaction boundaries are preserved.

## Every changed harness file

Paths below are relative to `scripts/validation/academic_setup/`.
All files in this originally untracked harness remain untracked; nothing was staged.

| Updated existing files | Added files |
| --- | --- |
| README.md | STAGE4B4.md |
| __main__.py | check_structure.py |
| inputs.py | concurrency.py |
| manifest.json | identity.py |
| policy.py | sql/prerequisite_violation.sql |
| session.py | sql/prerequisite_restore.sql |
| transport.py | sql/probes/snapshot_differences.sql |
| workflow.py | sql/probes/helpers.sql |
| sql/academic_probes.sql | sql/probes/tenancy_authority.sql |
| sql/security_probes.sql | sql/probes/lifecycle.sql |
| sql/snapshot.sql | sql/probes/audit_atomicity.sql |
| tests/support.py | sql/concurrency/setup.sql |
| tests/test_policy.py | sql/concurrency/synchronization.sql |
| tests/test_session.py | sql/concurrency/verify.sql |
| tests/test_workflow.py | sql/concurrency/teardown.sql |
| | tests/test_concurrency.py |
| | tests/test_deadlines_cleanup.py |
| | tests/test_identity.py |
| | tests/test_sql_contracts.py |

## Exact verification commands and results

Run from `F:\Git Project\CollegeAIChatbot` with Python bytecode generation disabled:

```powershell
python -B -m unittest discover -s scripts/validation/academic_setup/tests -v
python -B -m scripts.validation.academic_setup --check
python -B -m scripts.validation.academic_setup.check_structure
python -B backend/scripts/validation/check_structure.py
```

| Check | Result |
| --- | --- |
| Initial unit run | 57/58 passed; obsolete ordering assertion corrected |
| Intermediate unit run | 59 passed |
| Final guarded unit run | 61 passed, exit 0 |
| File-only preparation | PASS, 49 migrations / 106 pinned inputs, execution_authorized=false |
| Harness structure | PASS; every folder <=15 direct files and file <=250 lines |
| Backend structure | PASS, exit 0 |
| Preservation | 7,109 baseline files; no missing files or changes outside harness |

Unit tests block real subprocess spawning and network resolution/connections.
SQL contract tests inspect pinned text and orchestration; PostgreSQL does not run.
Mocked thread barriers verify that paired workers actually overlap and are joined.

New evidence is confined to `logs/backend/academic-stage4b4-verification/`:
`git-before.txt`, `before-sha256.json`, `unit-tests.log` (initial failure preserved),
`unit-tests-final.log` (59 tests), `unit-tests-guarded.log` (60 tests),
`unit-tests-reviewed.log` (final 61 tests),
`unit-tests-authority-final.log` (61 tests after the final authority case),
`preparation-authority-final.log`, `harness-structure-authority-final.log`,
`preparation.log`, `harness-structure.log`, `backend-structure.log`,
final structure/preparation logs, `preservation.json`, `git-after.txt`,
`changed-files.json` and `verification-commands.json`.
The command inventory records exact PowerShell capture wrappers and exit results.

The pre-existing `backend/app/core/application.py` hash remains
`752d5d58e28dced775a31ade0b9d8b5a8fd979fe68cdc6579faf346fb01e68db`.
Original evidence, unrelated tracked modifications, untracked files, migration
sources and B05/E23 governance artifacts were preserved. No Git staging, commit,
reset, clean, restore or stash was performed.

## Remaining blockers and coverage limits

- No real full image ID, engine ID, executable hash/version, image Config review,
  bootstrap evidence or PostgreSQL UID/GID has been established in this stage.
  Discovering/verifying runtime identity requires separately authorized operations.
  Synthetic pins in tests cannot supply this evidence.
- Catalog mutation detection, actual prerequisite rejection/transaction rollback,
  authority/lifecycle/audit SQL, privileges and all four races are prepared but
  **unexecuted**. Unit passes establish guard behavior and wiring only. SQL syntax,
  actual image bootstrap/extensions and engine metadata compatibility need live
  verification in a separately approved isolated stage.
- Hosted Supabase compatibility is untested. Live transport remains sealed and
  the CLI exposes no execution switch. Another review and separate explicit
  authorization are required before any container/database execution.
