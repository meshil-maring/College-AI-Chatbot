# Stage 4B-5 remediation report

Historical Stage 4B-5 results; execution remains disabled.
The later source review found retained-object and probe-contract gaps. Current
remediation and evidence are in [Stage 4B-5.1](reports/STAGE4B51.md).
This stage implements the six findings in the latest Stage 4B-4 independent
review. No Docker command, container operation, database connection, SQL or
migration was executed. There is no hosted fallback and no execution approval.

## Remediation and regression coverage

1. **Readiness:** retry pg_isready statuses 1 and 2 while within the deadline;
   status 3 and all other unexpected statuses fail closed. Tests cover 2 then 0,
   persistent 2 through the deadline, fatal 3, blocked subsequent SQL, and late
   successful readiness at every blocking operation.
2. **Deadlines:** remaining budgets reach version/engine/image/container
   inspections, readiness calls and runtime identity checks. SQL checks its
   deadline after completion as well as before submission. Transport checkpoints
   reject late successful results, including mocked delayed process creation.
   Client timeout reports an unverified outcome; no cancellation or rollback is
   inferred from killing the client. Python cannot interrupt process creation on
   every platform, so elapsed time can exceed a process timeout.
3. **Object inventory:** a full post-decommission inventory is stored separately
   from projected retained state. Exactly seven academic table names and nine
   exact routine signatures are approved additions; no sequences are approved.
   Inventory includes partitioned tables, views/materialized views/foreign tables
   and all public routine kinds, not just ordinary tables/functions. Missing or
   malformed inventory fails closed. Existing retained table state and full
   routine/sequence state were intended to remain protected. Correction: Stage
   4B-5's inventory compared names/kinds only; existing views/procedures and other
   non-ordinary kinds lacked full content comparison. Stage 4B-5.1 addresses this.
   Prepared negative controls add unexpected tables, a partitioned table,
   function, procedure and sequence; alter/drop retained tables, functions and
   sequences; and reject missing inventory. Each mutation is rolled back and
   restoration is compared before continuing. Unit tests compare the approved
   inventory with the actual pinned academic migration definitions.
4. **Catalog mutations:** prepared probes now disable an existing trigger, force
   RLS, alter a sequence definition, change its owner and grant sequence usage.
   Each uses the existing capture/difference/subtransaction rollback/restoration
   helper. The outer transaction also rolls back all fixtures.
5. **Database roles:** a private SECURITY INVOKER probe helper executes SET LOCAL
   ROLE, verifies current_user, captures exact expected SQLSTATE 42501 and resets
   the role on success and failure. The switched command never calls the private
   harness schema. All three API roles attempt INSERT/UPDATE/DELETE/TRUNCATE on
   all seven tables and execution of all six private application helpers.
   anon/authenticated attempt all three protected RPCs with valid payloads and a
   service JWT claim; the probe requires service_role success for those RPCs and
   exact audit evidence. None was executed. The generic denial-result jsonb
   assumption required correction for void/trigger helpers in Stage 4B-5.1.
   The original catalog privilege checks remain in place; no grants were relaxed.
6. **Concurrency audit:** setup retains the complete original parent row. Before
   teardown, tenant B creation requires exactly one audit for its record, matching
   action, actor, table, status, null before and the exact after row. Parent
   deactivation requires exactly two lifetime record audits (setup create plus
   deactivate), exactly one matching deactivation and exact before/after rows.
   Rejected child rows/audits remain forbidden. A mocked verification failure
   proves teardown is skipped, preserving evidence for the enclosing failure path.

The Python regressions are in tests/test_readiness.py (8 tests) and
tests/test_prepared_safeguards.py (8 tests). Existing
tests/test_deadlines_cleanup.py retains late-readiness/inspection coverage;
tests/test_sql_contracts.py now checks all five added catalog mutation controls.
The new probe stages are pinned and wired before concurrency. Mocked failure
tests prove either stage halts later work and invokes owned cleanup.
These SQL tests inspect text/contracts and orchestration only. They do not parse
SQL with PostgreSQL, switch real database roles, or prove actual probe behavior.

## All changed harness files

Paths are relative to scripts/validation/academic_setup/.

| Updated existing files | Added files |
| --- | --- |
| README.md | STAGE4B5.md |
| STAGE4B4.md | sql/probes/object_inventory.sql |
| inputs.py | sql/probes/privilege_roles.sql |
| manifest.json | tests/test_readiness.py |
| session.py | tests/test_prepared_safeguards.py |
| transport.py | |
| workflow.py | |
| sql/snapshot.sql | |
| sql/probes/snapshot_differences.sql | |
| sql/concurrency/setup.sql | |
| sql/concurrency/verify.sql | |
| tests/test_sql_contracts.py | |

There are 12 updated and 5 added harness files. No application, migration,
B05/E23 artifact, historical verification log or unrelated workflow was changed.
The only additions outside the harness are dedicated verification evidence under
logs/backend/academic-stage4b5-verification/. Its changed-files.json lists every
source/documentation change and all new evidence files.

## Exact verification commands and results

From F:\Git Project\CollegeAIChatbot, with bytecode writes disabled:

```powershell
python -B -m unittest discover -s scripts/validation/academic_setup/tests -v
python -B -m scripts.validation.academic_setup --check
python -B -m scripts.validation.academic_setup.check_structure
python -B backend/scripts/validation/check_structure.py
```

| Check | Result |
| --- | --- |
| Initial offline unit run | 75 passed, exit 0 |
| Final offline unit run | 77 passed, exit 0 |
| Manifest/file-only preparation | PASS; 49 migrations / 108 total pinned inputs; authorization false |
| Harness structure | PASS; at most 15 direct files / 250 physical lines |
| Backend structure | PASS, exit 0 |
| Preservation | 7,147 baseline files; none missing; no changes outside the harness |

Evidence includes both unit logs, preparation/structure logs, before hashes,
before/after Git state, preservation.json, changed-files.json and
verification-commands.json. The command inventory records exact PowerShell
capture wrappers, exit codes and the non-mutating preservation check source.
No original migration or external input pin was changed; only harness SQL pins
were refreshed and the two new SQL inputs were added. Tests block real process
spawning and socket access; tests that inspect the future live adapter replace
its process runner and temporary-directory creation with mocks.

## Preservation and corrected historical claims

All 175 original Git entries remain intact: 22 modified tracked files and 153
untracked files. The five additions produce 158 untracked files, including 49
untracked harness files; no files are staged. The index byte hash and staged diff
match the captured before-state. All 7,147 original files remain present;
only the 12 listed existing harness files have changed.

The pre-existing backend/app/core/application.py SHA-256 remains:
752d5d58e28dced775a31ade0b9d8b5a8fd979fe68cdc6579faf346fb01e68db

STAGE4B4.md now identifies the NOT READY review outcome and corrects its previous
overstatements about catalog mutation coverage, concurrency audits, actual role
execution and deadline enforcement. It also records the previous absence of an
approved additions inventory. Its historical test results are retained as history.

## Unresolved limitations and execution boundary

Real image/engine/executable/config/bootstrap pins and PostgreSQL UID/GID evidence
remain unavailable. SQL syntax, runtime grants and role-switch behavior,
bootstrap/extensions, catalog controls, transaction rollback, all four races,
database-side timeout/cancellation and cleanup remain unverified by a real engine.
Service-role reads still depend on backend tenant filtering; these mutation probes
do not establish backend read-path isolation. Hosted Supabase remains untested.

EXECUTION_AUTHORIZED remains False; manifest authorization remains false; the CLI
still has no execution option. Original isolation controls, exact identity pins,
49 migrations/order/transaction boundaries and owned cleanup are preserved.
No staging, commit, reset, clean, restore or stash was performed.
No database execution occurred. This report does not authorize execution.

See the Stage 4B-5.1 report for the current independent-review status.
