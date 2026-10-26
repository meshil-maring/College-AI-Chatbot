# Stage 4B-5.1 source remediation report

Status: **READY FOR INDEPENDENT REVIEW**. Execution remains disabled.
No Docker command, container operation, database connection, SQL, migration or
hosted Supabase access occurred. This report does not authorize execution.

## Verified source properties and changes

1. **Regex inspection:** the actual pre-change session.py/workflow.py patterns
   were valid, single-escaped expressions. There was no malformed double escape
   to correct. Exact AST-extracted source is archived in regex-source-before.json.
   Error matching now operates on individual stderr lines with horizontal
   whitespace and an actual ERROR/psql prefix, preventing cross-line and CONTEXT
   false positives. Expected messages remain regex-escaped and exact. Tests cover
   LF/CRLF, psql prefixes, metacharacters, wrong/split messages, literal backslash-r
   and SQLSTATE suffixes. The valid late_failure COMMIT regex is retained; LF/CRLF
   tests preserve every original byte outside the injected failure and reject
   duplicate boundaries, trailing text, literal escapes and missing final newline.
2. **Same-name catalog changes:** retained keys now compare metadata values, not
   just presence/kind. A focused pinned snapshots/catalog.sql module captures
   relation definitions/options, partition keys/bounds/parents, columns/column
   ACLs, owners, relation ACLs and relevant non-ordinary constraints/indexes/rules/
   triggers/policies. View/materialized-view definitions use pg_get_viewdef;
   foreign definitions are read only from catalogs, including server/wrapper
   metadata. No foreign rows are queried. All public pg_proc kinds are captured:
   functions, procedures, window functions and aggregates. Routine owner/ACL and
   pg_proc metadata are included; aggregates use pg_aggregate rather than calling
   pg_get_functiondef on an unsupported aggregate. Sequence definitions/owner/ACL
   remain covered. Existing row-state projection and added-object allowlists remain.
   Scope remains public relations/routines, auth.users, and public/auth sequences;
   this is not a claim of global cluster immutability or foreign data preservation.
   Prepared controls alter definition, owner and ACL under the same name for
   views, materialized views, partitioned/foreign tables, procedures, aggregates
   and window functions. Existing ordinary-table/function/sequence controls remain.
   Each control requires P4202, rolls back its subtransaction and compares full
   restoration; the outer transaction restores fixtures and snapshot baselines.
3. **Exact helper/RPC contracts:** offline tests derive all nine signatures and
   return types from the pinned three academic migrations, compare every private
   call and exact service grant/revocation, and check the row/audit source contract.
   Prepared SQL also checks function kind, scalar return type, owner, SECURITY
   DEFINER, search_path and per-role EXECUTE grants before exercising the controls.
   The denial path no longer coerces void/trigger returns to jsonb. It executes
   and discards the result, still requiring exact 42501; unexpected success or a
   different failure remains fatal. Only permitted RPC controls use INTO STRICT
   jsonb. Positive audit checks now include the actual relation name and returned
   institution, in addition to action, actor, record ID, status and before/after.
4. **Ownership/ACL mutations:** fixture owners and standalone-sequence dependency
   state are checked; the isolated postgres superuser and ability to SET ROLE to
   the new owner are required. The fresh owner receives fixture-schema CREATE/
   USAGE before measurement. Fixture-only ACL normalization makes measured grants/
   revocations non-no-ops: anon table/column/sequence rights are absent, PUBLIC
   EXECUTE on the fixture function is present, and auth CREATE is absent for the
   new role. The original difference helper still checks change and restoration;
   every fixture/grant/role is inside the outer rollback transaction.

The ownership preconditions were checked against the PostgreSQL 17
[ALTER FUNCTION](https://www.postgresql.org/docs/17/sql-alterfunction.html) and
[ALTER AGGREGATE](https://www.postgresql.org/docs/17/sql-alteraggregate.html)
documentation. This is source/documentation review, not runtime verification.

## Pinned role contracts

All functions below are in public. All nine are SECURITY DEFINER with empty
search_path; migrations revoke PUBLIC/anon/authenticated/service_role execution,
then grant only the three manage RPCs to service_role.

| Signature | Return | Probe expectation |
| --- | --- | --- |
| assert_academic_foundation_actor(uuid,uuid,text) | void | All three API roles denied |
| validate_academic_foundation() | trigger | All three API roles denied |
| validate_academic_structure() | trigger | All three API roles denied |
| guard_academic_structure_parent() | trigger | All three API roles denied |
| validate_academic_sections() | trigger | All three API roles denied |
| guard_academic_sections_parent() | trigger | All three API roles denied |
| manage_academic_foundation(uuid,uuid,text,uuid,jsonb) | jsonb | Browser denial; service control creates department |
| manage_academic_structure(uuid,uuid,text,uuid,jsonb) | jsonb | Browser denial; service control creates subject |
| manage_academic_sections(uuid,uuid,text,uuid,jsonb) | jsonb | Browser denial; service control creates section |

RPCs return after_row. Create audits contain null before and that exact after row.
Entity/action/relation mappings are departments/academic.departments.create/
departments, subjects/academic.subjects.create/subjects, and sections/
academic.sections.create/class_sections. The section API entity is not its SQL
table name. No required denial or application grant was weakened.

## Exact files changed

Paths below are relative to scripts/validation/academic_setup/.

| Updated files | New files |
| --- | --- |
| README.md | reports/STAGE4B51.md |
| STAGE4B5.md | sql/snapshots/catalog.sql |
| inputs.py | sql/probes/catalog_retention.sql |
| manifest.json | tests/test_source_review.py |
| session.py | |
| workflow.py | |
| sql/snapshot.sql | |
| sql/probes/privilege_roles.sql | |
| sql/probes/snapshot_differences.sql | |
| tests/test_session.py | |
| tests/test_workflow.py | |
| tests/test_prepared_safeguards.py | |
| tests/test_sql_contracts.py | |

There are 13 updated and 4 new files. Dedicated evidence is added only under
logs/backend/academic-stage4b51-verification/; changed-files.json lists it all.
The focused SQL module and reports subfolder keep the existing root within its
15-file limit. No existing paths were moved or deleted.

## Safe validation and preservation

Run from F:\Git Project\CollegeAIChatbot, with bytecode writes disabled:

```powershell
python -B -m unittest discover -s scripts/validation/academic_setup/tests -v
python -B -m scripts.validation.academic_setup --check
python -B -m scripts.validation.academic_setup.check_structure
python -B backend/scripts/validation/check_structure.py
```

Both initial and final offline unit runs passed 87 tests, exit 0. Exact capture
wrappers/exit codes are recorded in verification-commands.json. The manifest
contains the unchanged 49 migrations and 110 total pinned inputs: only harness
SQL hashes changed and the two focused SQL files were added. No external input
or migration pin was changed. Unit tests prohibit real process/socket I/O and
replace future live-adapter process calls with mocks.

| Final check | Result |
| --- | --- |
| Offline unit suite | 87 passed, exit 0 |
| File-only preparation | PASS, 49 migrations / 110 pins, exit 0 |
| Harness structure | PASS, maximum 15 files / 248 physical lines, exit 0 |
| Backend structure | PASS, exit 0 |
| Preservation | PASS, 7,165 baseline files present, no changes outside harness |

The new tests comprise two LF/CRLF error tests, one boundary-rejection test, and
seven source/contract tests. Existing tests also cover positive LF/CRLF byte
preservation, safe probe ordering, failure cleanup and the new stage's failure
before concurrency. Static SQL checks are not PostgreSQL parsing or execution.

The preservation baseline contains 7,165 existing files and 180 original Git
entries. All original entries and staged/index state remain intact. Only the 13
listed existing harness files changed, with four new untracked harness files.
Git now has 22 modified tracked files and 162 untracked files (53 in the harness),
with nothing staged. Both the staged diff and index byte hash are unchanged.
The existing application.py SHA-256 remains:
752d5d58e28dced775a31ade0b9d8b5a8fd979fe68cdc6579faf346fb01e68db

## Unresolved execution blockers

Real image/engine/executable/bootstrap/UID/GID evidence is still absent. A real
PostgreSQL run is required to establish SQL syntax, metadata representations,
deparser/DDL compatibility, window/aggregate/handlerless-foreign fixture support,
actual role-switch and trigger-function denial ordering, permission preconditions,
audit behavior, transaction rollback/restoration, concurrency and cleanup.
The prepared SQL requires those checks; offline passes do not establish them.
Foreign data and hosted Supabase were not accessed. Client timeout still means
unknown outcome, not verified database-side cancellation or rollback.

EXECUTION_AUTHORIZED remains False, manifest authorization remains false and the
CLI has no execution option. Isolation controls and owned cleanup are preserved.
No application/migration/B05/E23/unrelated workflow was changed. No staging,
commit, reset, clean, restore or stash occurred. No database execution occurred.

**READY FOR INDEPENDENT REVIEW**
