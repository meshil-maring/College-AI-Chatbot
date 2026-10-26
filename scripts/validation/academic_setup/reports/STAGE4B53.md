# Stage 4B-5.3 targeted source-only remediation

Status: prepared for another independent read-only review; execution disabled.
No Docker operation, container, database connection, SQL execution, migration or
hosted Supabase access is authorized or performed by this remediation.

## Four findings

1. Concurrency finalization performs no application-row deletion. The pinned
   Phase 8.1 append-only audit trigger and all production authorization remain
   untouched. Two synthetic race worlds and all their application rows/audits
   remain intentionally until owned disposable-container destruction. Setup
   registers 23 exact retained rows: eight principals/roles and 15 audits.
   Verification checks all five race audits before registering them, giving 28
   exact retained rows, including 20 audits. The in-memory retained comparison
   removes only these exact registered rows; changed/missing registered rows and
   unregistered additions fail. It does not exclude an entire tenant or recapture
   the retained baseline. Failure leaves fixtures/evidence for container cleanup;
   uncertain cleanup remains INCOMPLETE and requires manual review.
2. Error matching requires exactly one error record and the expected state and
   optional exact message. The only accepted psql location is `<stdin>:<positive
   line number>`, matching the fixed `psql -f -` transport. Arbitrary colon text,
   malformed/duplicate error records and psql-prefixed CONTEXT cannot supply
   provenance. Normal located NOTICE/WARNING output and verbose error context
   remain accepted. LF/CRLF and literal/control-character cases have regressions.
3. Before the first decommission submission, snapshot.sql installs explicit
   synthetic fixtures and captures an original retained inventory containing all
   declared relation/routine kinds and sequences. Successful decommission compares
   capture(false), including its inventory, with this original baseline. The
   later post-decommission/academic baselines remain distinct. Only the sanctioned
   staff-delegation routine body/deparsed definition is projected out; its owner,
   ACL and remaining routine metadata are retained. Student ancestry columns,
   retired objects/owned sequences and existing sanctioned row/trigger/index
   projections remain explicit. Same-name controls run after original destructive
   DDL/checks and before final COMMIT inside a forced-P4001 rollback variant.
   Each requires exact P4202 detection, even after deliberately rebasing the later
   academic snapshots, and proves full restoration after subtransaction rollback.
4. Catalog capture now includes ordinary rewrite definitions/enabled state,
   table-level replica identity/tablespace, non-ordinary index validity/readiness/
   clustering, foreign-column options, foreign-server type/version, and sequence
   OWNED BY dependencies/persistence. Existing ordinary-index flags remain covered.
   Targeted DDL controls exercise rules, replica identity, ordinary/materialized
   clustering, foreign-column options, server version/type, sequence ownership
   association and logged/unlogged persistence. Server TYPE uses same-name fixture
   recreation with its other schema/options/grants restored.

## PostgreSQL 17 control limitations and declared scope

The retained scope remains public ordinary/partitioned/foreign relations, views,
materialized views, all public pg_proc kinds, auth.users and public/auth sequences,
plus the existing schema/default-ACL checks. Only ordinary-table/auth.users rows
are read. Foreign tables use a handlerless wrapper/server without endpoints or
user mappings; foreign rows are never read. Prerequisite preservation fixtures,
their owner role/server/wrapper and the original legacy fixture remain until
disposable-container destruction, as do committed concurrency fixtures.

All applicable index validity/readiness/clustering fields are captured. PostgreSQL
17 has no supported ALTER INDEX setter for validity/readiness. Failed concurrent
index builds cannot run inside this rollback-only transaction and would introduce
uncertain intermediate state. Prepared metadata perturbations test those flags
through the actual comparison helpers for ordinary, materialized and partitioned
fixtures without writing system catalogs. These are comparator controls, not proof
of an observed PostgreSQL index-state transition. Real CLUSTER ON DDL controls
cover ordinary/materialized clustering; partitioned index clustering is not a
supported physical-clustering operation, so its flag uses metadata perturbation.
Views and foreign tables have no local indexes. Sequence counters remain outside
row preservation; OWNED BY metadata and persistence are protected independently.
No global cluster immutability or foreign-data preservation is claimed.

Documentation reviewed: PostgreSQL 17
[index catalog](https://www.postgresql.org/docs/17/catalog-pg-index.html),
[ALTER MATERIALIZED VIEW](https://www.postgresql.org/docs/17/sql-altermaterializedview.html),
[ALTER SERVER](https://www.postgresql.org/docs/17/sql-alterserver.html),
[ALTER SEQUENCE](https://www.postgresql.org/docs/17/sql-altersequence.html), and
[column catalog](https://www.postgresql.org/docs/17/catalog-pg-attribute.html).
Documentation/source checks are not PostgreSQL execution.

## Exact changed files

All paths below are relative to scripts/validation/academic_setup/.

| Path | Reason |
| --- | --- |
| README.md | Current stage, original-baseline ordering and fixture lifetime |
| inputs.py | Require the four new pinned SQL modules |
| manifest.json | Refresh only harness SQL pins; add four SQL inputs |
| session.py | Strict single-record error provenance |
| workflow.py | Compose snapshot modules and inject rollback-only decommission controls |
| sql/snapshot.sql | Always capture catalog inventory and project exact race rows |
| sql/snapshots/catalog.sql | Capture the reported missing catalog properties |
| sql/snapshots/retained.sql (new) | Original retained projection, comparison and restoring controls |
| sql/snapshots/fixtures.sql (new) | All-category preservation fixtures before decommission |
| sql/retained_verify.sql | Use the original complete retained comparison |
| sql/probes/decommission_retention.sql (new) | Same-name definition/owner/ACL controls before COMMIT |
| sql/probes/catalog_properties.sql (new) | Property DDL and index-metadata comparator controls |
| sql/concurrency/setup.sql | Exact committed fixture registry and projection |
| sql/concurrency/verify.sql | Verify and register exact race audit rows |
| sql/concurrency/teardown.sql | Finalize retention checks without prohibited deletion |
| tests/test_session.py | Spoofing/malformed errors and legitimate verbose-output regressions |
| tests/retained_state/__init__.py (new) | Focused regression package within folder limits |
| tests/retained_state/test_preservation.py (new) | Baseline ordering, controls and audit-safe finalization regressions |
| reports/STAGE4B53.md (new) | This report and explicit protection/runtime limits |

Evidence is confined to logs/backend/academic-stage4b53-verification/.

## Validation and preservation

Initial and final offline suites: 99 discovered, 95 passed, zero failures/errors,
four skipped. The skipped pre-existing adapter tests mock authorization True;
their sources were inspected, and the flag remained false throughout this stage.
Twelve new test methods cover the four findings. Other tests block real subprocess/
socket I/O. File-only preparation passes with the unchanged 49 migrations and
114 total pins. Harness and backend structure checks pass: maximum 15 directly
contained files and 246 physical lines.

Preservation checks retain all 7,183 baseline files, original Git entries, staged
diff and index bytes. Exactly 12 existing harness files changed and seven harness
files were added. No application, migration, B05/E23, historical evidence or
unrelated file changed; external pins are unchanged. Dedicated evidence contains
the exact changed-file inventory/after hashes, commands, logs and preservation
results. No staging, commit, reset, clean, restore or stash occurred.

Application.py must retain SHA-256:
752d5d58e28dced775a31ade0b9d8b5a8fd979fe68cdc6579faf346fb01e68db

## Remaining blockers

Prepared SQL syntax, catalog representations, DDL preconditions, role switching,
audit effects, actual transaction rollback, concurrency and owned cleanup require
real PostgreSQL validation in a separately authorized stage. Real engine/image/
executable/config/bootstrap pins and UID/GID evidence remain absent. Client timeout
still establishes no database cancellation/rollback. Hosted compatibility is
untested. The source flag and manifest remain false; no execution CLI exists.
Offline passes establish source consistency and mocked behavior only.

Stop for another independent read-only review. This report grants no execution
authorization.
