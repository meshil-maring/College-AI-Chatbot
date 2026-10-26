# Academic Setup Stage 4B-5.3 source remediation harness

**PREPARED ONLY. No container, database, SQL or migration execution is authorized.**
The CLI reads local pinned files only. `LiveTransport` is sealed by
`EXECUTION_AUTHORIZED = False`; the CLI has no execution, endpoint, database,
credential, target-container or image override option. Unit tests use synthetic
Docker metadata, block real subprocess/socket calls, and never import the app.

From the repository root:

```powershell
python -B -m scripts.validation.academic_setup --check
python -B -m unittest discover -s scripts/validation/academic_setup/tests -v
python -B -m scripts.validation.academic_setup.check_structure
python -B backend/scripts/validation/check_structure.py
```

Stage 4B-5.3 output belongs under `logs/backend/academic-stage4b53-verification/`. A passing
preparation/unit check does not establish PostgreSQL compatibility or authorize
execution. Do not invoke other existing live runners to bypass this stage.

## Ownership and design review

`scripts/validation/disposable_container.py` supplies the existing fixed endpoint,
image reference, identity syntax and bounded tmpfs policy. Its live context-based
selection and ownership-only cleanup are deliberately not used by this harness.
The utility, its purpose allowlist, old decommission/reset runners, B05/E23
governance records and historical migrations remain unchanged.

The owned modules are:

| Module | Responsibility |
| --- | --- |
| `policy.py` | Immutable approval pins, exact startup command and isolation constants |
| `identity.py` | Required executable/version/config/bootstrap evidence and runtime identity |
| `concurrency.py` | Synchronized pairs of future socket sessions, bounded and joined |
| `check_structure.py` | Non-mutating harness file/folder limits and Python syntax |
| `transport.py` | Fixed endpoint, engine/image checks, private config, bounded subprocesses |
| `metadata.py` | Same strict target checks before startup, SQL and cleanup |
| `session.py` | Future create/start/readiness/SQL/cleanup lifecycle; no automatic invocation |
| `inputs.py` | Local-only paths, raw-byte hashes, exact migration inventory and SQL inputs |
| `workflow.py` | Separate-file replay, deliberate rollback and retained-data verification |
| `__main__.py` | File-only review command |
| `sql/`, `tests/` | Unexecuted database contracts and offline guard tests |

The user supplied the image ID as `sha256`. This is incomplete and is never
treated as approval of a tag or guessed digest. Future runtime construction
requires a full `sha256:` plus 64 lowercase hex digits, approved engine ID,
absolute local `docker.exe` path, and reviewed non-root PostgreSQL UID/GID.
None is discovered by the preparation command. Test IDs/UIDs are synthetic.

## Future containment contract

Only `npipe:////./pipe/dockerDesktopLinuxEngine` is accepted. There is no context
selection, endpoint fallback, pull, build, Compose, Supabase CLI or host DB client.
Engine identity, `docker-desktop`, Linux and amd64 are checked again before each
operation. The approved local tag
`public.ecr.aws/supabase/postgres:17.6.1.166` must still resolve to the full pinned
image ID; creation uses that ID with `--pull=never`.

Creation and startup are separate. A cryptographically fresh 32-hex run token,
full-token name and exact disposable/run/purpose/harness labels identify the
run. The full 64-hex ID must come from this run's successful create response.
No existing target, shortened ID, name lookup or guessed cleanup is accepted.
A lost/ambiguous create response is INCOMPLETE and needs manual investigation;
the harness does not enumerate or remove possible matches.

The create specification enforces:

- `--network none`, no published ports, no additional attached networks;
- no host binds, persistent/named/anonymous volumes or inherited storage;
- one data tmpfs at `/var/lib/postgresql/data`, exactly 536870912 bytes (512 MiB),
  with `rw,noexec,nosuid,nodev`, reviewed UID/GID and mode 0700;
- a read-only root filesystem, non-root user, all capabilities dropped,
  `no-new-privileges`, private IPC/cgroup namespaces and no host namespace sharing;
- `--rm`; no device access, privilege overrides or additional mounts.

An image-declared data volume is accepted only when covered by that exact tmpfs;
additional image volumes refuse creation. Container inspection accepts the known
empty or mirrored-tmpfs mount representations, and unpublished image port
declarations, while refusing any actual host binding. Missing required metadata
fails closed. Exact metadata spellings must be reviewed against the actual
engine before runtime approval; unknown representations are not relaxed silently.

The entrypoint is overridden with `/usr/bin/env -i`; bundled image initializers
are bypassed. The reviewed command will run `initdb` as the approved postgres UID
using `/usr/lib/postgresql/17/bin`, then start postgres with **no TCP listener**.
Socket and data live in the same tmpfs; local auth is trust, host HBA is reject,
and socket permissions are 0700. No password is required, generated or logged.
These binary paths and extension availability are currently unverified.

The live adapter, if separately approved later, supplies a fresh empty Docker
config and an OS-only environment. It never loads dotenv, app configuration,
database drivers or hosted service credentials. Every `docker exec` also uses
`env -i`; psql receives `-X --no-password`, explicit socket/user/database, and
`ON_ERROR_STOP=1`. There is no DSN, TCP or provider fallback. Raw process output,
SQL errors, passwords and environment contents are never printed by the harness.

## Future ordered database verification

`manifest.json` pins the exact 49 migrations and supporting inputs by SHA-256 over
raw bytes. The inventory includes **all 45 preceding migrations**, including the
two historical B05/approval files. Nothing is skipped, rewritten or substituted;
no B05 containment candidate, successor or deployment adapter is executed.
The four academic generators/source manifests/fragments are also pinned.
Source parity checks should be repeated before approval; the manifest provides
consistency, not independent approval or runtime compatibility evidence.

After explicit approval and completed identity/startup review, the planned order is:

1. Load and hash all inputs before lifecycle work. Verify local engine/image,
   create an isolated container, inspect it, then separately validate and start.
2. Wait for local socket readiness. Verify PostgreSQL 17.6, data/socket paths,
   absence of a TCP listener and rejecting host HBA. Install the synthetic local
   Auth/role shim and pinned vector 0.8.0 / btree_gist 1.7 extensions.
   This minimal shim does not reproduce hosted Auth, gateway, RLS claims or APIs.
3. Replay the **45 files before `20261023000000`** in filename order. One psql
   process reads each original file through stdin with `-f -`. Never use `-c`
   for a whole file, `-1`, one transaction for the sequence, or retries after an
   error. Each migration retains its own explicit or implicit boundaries.
   A nontransactional migration can partially apply before failing; discard the
   entire lane rather than resume it. No Supabase deployment ledger is fabricated.
4. Install the pinned existing synthetic legacy fixture
   `../academic_decommission/seed.sql`, subject to review with this package.
   It uses `@example.invalid` identities and includes retained accounts, a student
   profile, nonacademic grants, legacy masters and package memberships. It is
   never installed in application/hosted databases. The old `approval.sql` and
   `contracts.sql` are deliberately outside this plan.
5. Install synthetic retained-object catalog fixtures and snapshot all legacy public rows, synthetic `auth.users`, table columns,
   constraints/RLS flags, triggers, policies, indexes, object ownership, column/table/namespace/default ACLs and public function definitions/ACLs inside the container.
   Take a second retained-state projection excluding only retired domain objects,
   academic permissions, the two removed student keys and the sanctioned staff
   delegation function body replacement. Full retained catalog metadata is captured
   before the first decommission submission. Do not print snapshot contents.
6. First add an unexpected preserved-table FK into the legacy domain. Run the original decommission file and require its exact prerequisite refusal message and SQLSTATE P0001. Compare the full snapshot in a fresh session before removing the fixture FK and refreshing the rollback baseline. Run an in-memory negative variant of decommission: insert unique SQLSTATE
   `P4001` immediately before its own final COMMIT. Accept only psql exit 3 with
   that exact state. A new socket session must prove legacy rows/schema/routines
   restored. The source migration and its outer transaction stay unchanged.
7. Apply `20261023000000_decommission_academic_domain.sql` unchanged. Verify all
   39 retired tables are absent and retained account/nonacademic state matches
   the pre-decommission projection. Verify the synthetic student identity remains.
8. Apply unchanged, in order:
   `20261023010000_academic_foundations.sql`,
   `20261024000000_academic_structure.sql`,
   `20261024010000_academic_sections.sql`.
   These and decommission are the **four academic migrations**.
9. Run rollback-only probes for the CSE → B.Tech CSE → 2026–2027 → Fifth Semester
   → one Section A → three reusable subjects example; uniqueness, immutable
   ancestry, soft removal/reactivation/idempotency, parent deactivation,
   unauthorized actor refusal and Academic Setup mutation/audit atomicity.
   Probe all seven tables for RLS/browser denial/service SELECT-only grants,
   and all three mutation entry points for service-only execution. Compare the
   original retained tables/routines again, allowing new academic objects only.
10. Before cleanup, recheck engine/image/full ID/labels/isolation. Stop the running
    exact owned ID for automatic removal, or remove a never-started created ID.
    Confirm removal using a successful full-ID-filtered, untruncated container listing on the revalidated engine; accept only empty output. No forced removal, volume removal, name search or cleanup retries are used.
    Any mismatch, Docker timeout, inspection failure or uncertain cleanup reports
    INCOMPLETE and leaves the target untouched for manual review.

Prepared probes now include foreign-tenant actors/records/parents, permission provenance and delegated grants, inactive principals, lifecycle ordering, reactivation, all three mutation APIs under exact audit-constraint refusal, and catalog privilege/owner/function configuration checks. Four synchronized two-session lanes cover duplicate commits, parent deactivation versus child creation, tenant independence, and successful writes after the holder rolls back. The holder observes actual PostgreSQL blocking before release; the independence lane requires another tenant to commit while the first transaction holds its lock. These SQL probes have not been executed. PostgreSQL behavior, broader SQL lint and hosted compatibility remain unverified. No new
student rejection, approval, audit schema or account RPC implementation is added.

## Failure and approval boundary

Docker metadata operations have 20-second process timeouts, readiness uses a
60-second loop deadline with bounded inspections and 5-second readiness calls,
SQL calls have a 120-second inspection/execution budget, and stop has a 10-second daemon grace
within a 20-second process timeout. There are no mutation/SQL retries. Every blocking version/engine/image/container inspection, readiness call and runtime identity probe rechecks the monotonic readiness deadline. Late successful readiness fails closed. SQL separately rechecks its monotonic budget after inspections and immediately before submission; completed readiness does not impose a 60-second lifetime on later migrations.
Timeout means unknown outcome, not proof of successful cancellation in Docker.
SQL/start failures poison the session; only strict validated cleanup remains.
Readiness retries pg_isready statuses 1 (rejecting) and 2 (no response), bounded by
its deadline; status 3 is fatal. Every inspection and identity/readiness call
receives the remaining budget. SQL checks its deadline again after completion.
Python cannot interrupt process creation on every platform; elapsed time can
exceed a subprocess timeout. Late results fail closed. A killed Docker client
does not prove database-side cancellation or rollback; those remain unverified.

Still required: a full approved image ID, engine ID/executable and startup/UID/GID
verification, fixture/probe review, actual engine metadata review, and explicit
approval before enabling any live transport or container/database execution.
Unit passes do not remove these blockers.

## Stage 4B-4 review baseline and blockers

The findings list supplied with the Stage 4B-4 request is the complete Stage 4B-3
review baseline. No separate review artifact is assumed or created.

All identity pins are mandatory: full immutable image ID, fixed engine ID,
absolute local executable path and byte fingerprint, client/server versions,
canonical SHA-256 of the entire inspected image Config, reviewed bootstrap command
fingerprint, and PostgreSQL UID/GID. The image Config fingerprint binds image
User, Entrypoint, Cmd and Env as well as declared storage. The approved command
bypasses the bundled entrypoint; its full digest must match START_COMMAND.
Runtime checks compare exec UID/GID, all four PID 1 real/effective/saved/filesystem
UIDs/GIDs and both postgres/initdb versions before accepting readiness and again
before each SQL submission. Linked executable paths and changed bytes refuse I/O.
No real pins have been established in Stage 4B-4: only offline checks are allowed.
Synthetic test pins are never production evidence. Live transport stays sealed.

`sql/probes/snapshot_differences.sql` contains transactional mutation checks for
triggers, policies, indexes, ownership, table/column/routine/schema/default ACLs.
Each requires capture(true) to change and verifies restoration after a forced
subtransaction rollback. Unit tests check wiring and coverage statically; they
cannot prove catalog behavior without the separately approved SQL stage.
The retained projection excludes retired objects, sanctioned retired-helper
triggers, internal triggers owned by retired/new academic FKs, academic permissions,
and the removed student ancestry columns/indexes. Sequence ownership, ACLs and
definitions are included; nontransactional sequence counters are not row state.
Full rollback snapshots include all of those objects. Stage 4B-5 adds mutation
controls for an existing trigger's enabled state, forced RLS, and sequence
definition/owner/ACL, each checked before and after subtransaction rollback.

The post-decommission full inventory is separate from projected retained state.
Only seven explicitly named academic tables and nine exact routine signatures
may be added; no new sequences are approved. Unexpected additions and retained
object removal/change have rollback-only negative controls. Full baseline
routines/sequences have prepared preservation assertions, including projected-out routine names.
Prepared role probes use SET LOCAL ROLE and verify current_user, exact 42501
denials, role restoration, and successful service_role RPCs with audit evidence.
Commands executed as API roles never call the private harness schema. All seven
tables and all six private helpers are covered; browser roles are denied all
three RPCs. Tenant B creation and parent deactivation require exact audit counts,
actions, record IDs, actors and before/after rows before concurrency teardown.

All new SQL is raw-byte pinned. The original 49 migration hashes, order and
per-file transaction boundaries are preserved. Concurrency fixtures commit only
synthetic disposable data to enable separate sessions; finalization preserves their
append-only audits and principals until container destruction, comparing only exact
registered fixture rows apart from original retained state. A race failure
halts later lanes, joins both bounded workers and invokes strict owned cleanup
in a future execution stage. There is no endpoint/hosted fallback.

No Docker command, container operation, database connection, SQL or migration was
run in this stage. The schema remains unapplied. Another review is required;
container/database execution needs separate explicit authorization and verified
real identity evidence. See STAGE4B4.md for corrected historical claims and
STAGE4B5.md for historical results and reports/STAGE4B51.md for current source
properties, remediation, changed files, commands and unresolved runtime limits.

Stage 4B-5.3 source changes, exact files, controls, fixture lifetimes and catalog
coverage limits are documented in [reports/STAGE4B53.md](reports/STAGE4B53.md).
The original retained baseline, successful decommission comparison and later
academic replay baseline remain distinct. Same-name controls run inside a forced
rollback decommission variant; later rebasing cannot replace the original baseline.
All SQL remains unexecuted. PostgreSQL validation and real identity evidence are
still blockers; no offline result authorizes execution.
