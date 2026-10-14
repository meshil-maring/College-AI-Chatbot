# B05 Stage 1.10 source remediation package

Prepared 2026-10-12 Asia/Calcutta. **PREPARED ONLY / NOT RUN.** This package
authorizes no execution. Docker, PostgreSQL, extensions and provider behavior
have not been probed. This is a harness contract, not a security acceptance report.

`prepare.py` is a dedicated, file-only runner: it verifies the pinned inventory
and emits the intended replay plan. It has no execution option, subprocess,
database driver, network client or environment/credential loader. It has not
been run. `runner_contract.json` specifies the later executor's requirements;
there is no executable database runner in this stage. The existing
`disposable_container.py`, purpose allowlist and all other runners are unchanged.
No generic purpose flag or existing runner may be used to execute this package.

Preparation path checks reject absolute/drive-relative, UNC/device/network,
traversal, alternate-stream and ambiguous filename syntax before filesystem
metadata access. The repository must be on a Windows fixed/RAM disk, classified
by the local GetDriveTypeW API before any lstat; mapped/remote/unknown/removable
drives and non-Windows hosts fail closed. Each drive-root/repository/target
component is inspected with lstat; symbolic links and all reparse attributes
are rejected before traversing that component. No resolve operation is used.
The manifest, contract and migration directory use the same gate, and the pinned
input set is explicit. These checks assume a trusted Python runtime and a stable
local checkout: they are not an OS sandbox against concurrent directory swapping.
The future adapter must use private stable input staging and verify approved
manifest/source bytes immediately before use; the manifest is consistency data,
not self-authenticating approval evidence.

`test_preparation_safety.py` contains offline unit checks of path denial ordering
and synthetic fixture uniqueness/linkage. Importing definitions for those checks
does not call main/preparation_plan or run the harness. They do not implement or
validate an adapter. Runtime matrix cases remain NOT RUN regardless of unit results.

The manifest pins all 40 source migrations in filename order, the original
stopped candidate, the stopped post-B05 successor, the shared safety guard,
and package inputs with SHA-256 over raw bytes (no newline normalization).
The separately named `containment_successor.validation.sql` is an exact-byte
copy of the successor. Both stops, all pre/postconditions and final `ROLLBACK`
remain. It belongs outside `supabase/migrations` and receives no ledger version.
The historical candidate's 39-version/11-column expectation is not changed.
The successor expects 40 versions and the 12-column audit including decision_key.

Intended later order, after separate authorization:

1. Verify package/source hashes, exact migration set and local engine ownership.
2. Create a fresh run-owned container and fresh cluster using the contract.
3. Apply `bootstrap.sql`; replay manifest entries 1-39 unchanged as postgres.
4. For an upgrade-data lane, load `fixtures_pre_b05.sql` here; for an empty-chain
   lane, load it after entry 40 instead. Replay B05 as its own BEGIN/COMMIT file.
5. Load `fixtures_post_b05.sql` only after B05, then capture baseline catalogs,
   effective privileges, role reachability, all overloads and synthetic rows.
6. Run the stopped-copy refusal lane. Successor body validation requires a
   **new independently reviewed copy**, with exact stop replacements/transaction
   handling and new hashes explicitly approved later. Never strip stops at run
   time. The unchanged validation copy currently cannot reach the body.
7. Execute only approved rows of `test_matrix.md`, in independent fresh lanes.
   Capture outcomes and unconditional cleanup evidence; any cleanup failure
   makes the run incomplete. No fixture PASS or real-environment evidence exists.

Bootstrap specification: the existing guard's PostgreSQL tag is a reference only.
Supply independently reviewed repository@sha256 and content image ID pins for
linux/amd64 before execution. Later authorization must include local image inspect,
matching digest/ID/platform and required binary/extension-file verification.
Create only from that immutable digest with pull=never; absence/mismatch refuses
creation, without pulling, building, downloading or substituting. Both pins remain
unset and availability UNVERIFIED. A bare `initdb` cluster bypasses bundled Supabase
initializers; otherwise hidden roles/defaults/ledger could contaminate replay.
Run as the image's postgres OS user; PGDATA and the Unix socket both live under
the sole 512 MiB data tmpfs. A reviewed startup shim must set ownership/mode on
that exact mount (postgres, 0700) before dropping from the container's root user
to postgres for initdb/server startup; no recursive host path operations. Use
local-only trust authentication, reject all TCP HBA entries, socket mode 0700,
and run every psql process as the postgres OS user. No database password is
needed or loaded. Proposed exact versions are PostgreSQL 17.6,
vector 0.8.0 and btree_gist 1.7. These are requirements, not observed installed
versions. Confirm that the approved image includes matching extension control,
SQL and shared libraries; incompatible/missing dependencies must fail, without
downloads, substitutions or skipped migrations. Review amended pins if needed.
Locale C, UTF-8, UTC, no TCP listener and no image init scripts make bootstrap
repeatable once that image pin is accepted. pgcrypto is not a chain dependency:
gen_random_uuid is built into PostgreSQL 17. Vector must be in extensions;
the chain needs vector(1536), cosine operators and its index operator classes.

Auth is a synthetic SQL shim (`auth.users`, uid/role/jwt/email), not GoTrue or
JWT verification. Scalar request claim settings and JSON claims are supported;
each test sets role and claims transaction-locally and resets on exit. Tests
must SET ROLE to exercise ACLs: changing auth.role alone while remaining postgres
does not test service/client access. A service JWT subject is never substituted
for a human backend actor. Secret-key/PostgREST routing is a pending integration
contract and cannot be proven by this shim. No provider or gateway is started.

Migration history: the shim creates an empty `supabase_migrations.schema_migrations`
with version/name/statements columns. A future adapter must insert one entry
**only after** that exact file successfully completes, using the manifest's
version/name and original SQL statements, and independently record its byte
hash. Never prepopulate all 40 rows, mark a failed/rolled-back file applied, or
record the successor as a historical migration. Since B05 commits internally,
a ledger-write failure cannot undo that commit: fail the lane and destroy the
container rather than retrying against a partially recorded cluster. The
ledger shim is a local convention, not evidence of Supabase CLI equivalence.
Use separate psql processes with `-X`, ON_ERROR_STOP=1 and explicit socket/db/user;
never `--single-transaction` around B05 or around the full chain. Each session
starts with row_security=on, check_function_bodies=on, public/extensions search
path and bounded timeouts; baseline SET statements must not leak into later
sessions. The baseline itself clears SQL timeouts: an external per-process
deadline must still terminate the SQL client and fail/destroy the lane. Do not
edit migrations to enforce those settings. The future adapter must obtain one
fixture_anchor from the isolated server clock, pass it explicitly to both fixture
sessions, and reject missing/invalid anchor input; relative times avoid a
fixed-date fixture silently expiring before later authorization.

Fixtures are entirely synthetic: reserved example.invalid addresses, fixed UUID
namespaces and an explicit session anchor for relative expiry. Role rows absent
from the empty structural baseline are seeded as fixture data; deployed seed
availability is not inferred. No source export, .env, credentials, Supabase CLI,
Auth API, encryption service or delivery worker is used. Pre-B05 fixtures cover
legacy accepted/expired/cancelled gaps without fabricating operation history.
The staff invitation (suffix 6) uses staff-recipient@example.invalid, confirmed
synthetic user/Auth suffix 12 and approved membership suffix 6, with no grant.
The existing-account admin invitation (suffix 1) retains existing-a@example.invalid.
This satisfies the institution + lower(email) pending unique index, which does
not distinguish roles. Historical faculty/accepted/expired/cancelled gaps remain.
Post-B05 fixtures use owner-only inserts for isolated interruption snapshots;
they do not attest that RPC transitions can produce those snapshots. Sanctioned
transition tests must build their states through actual RPCs in separate lanes.

The precise future adapter specification is `runner_contract.json` version 3.
Pin the trusted absolute Docker CLI and hash, use explicit --host with the exact
local named pipe and a private reviewed --config directory, and record/recheck the
approved engine ID. desktop-linux is informational only: never select operations
through a mutable context. Use argument vectors without a shell or PATH lookup;
construct a minimal reviewed child environment without Docker/provider/PG overrides,
user config, credentials or CLI helpers/plugins. Named-pipe permission is daemon-wide
authority; ownership labels are not a boundary against a hostile daemon administrator.

Create before start, record full 64-hex ID and cryptographically fresh 32-hex token,
name/purpose/ownership labels and immutable image identity, and recheck before each
operation. Lost create responses may recover an ID only through a fresh exclusive
cidfile plus a matching same-engine create event and complete ownership inspection;
contradictory/missing provenance is INCOMPLETE, never a guessed target. Pin and
validate every relevant Config/HostConfig/Mounts/NetworkSettings field, including
auto-removal, privilege/capability/security profiles, devices/requests/cgroup rules,
private namespaces, network=none/attached networks and no published ports. Require
no binds/volumes/inherited storage or Docker socket, the sole 512 MiB hardened
PGDATA tmpfs, and no external data/WAL/tablespace/log path. Unknown field/default
representations require independent version-specific review, not implicit acceptance.
Startup may retain only CHOWN/SETUID/SETGID after dropping all default capabilities;
the reviewed shim must drop root and effective capabilities before postgres/psql.
Verify actual mount options/capacity, process identities, HBA and socket/server
settings after metadata acceptance. This specification does not claim the current
image or existing guard already meets these requirements.

SQL uses only docker exec --user postgres on that owned full ID, psql -X,
ON_ERROR_STOP=1 and the exact Unix socket/database/user. No DSN/URL/host input,
existing-container override, TCP fallback, host psql or connection-file input.
Fixture identities cannot leave the synthetic lane as reusable credentials.

Use an external monotonic deadline and a separately reviewed in-container
supervisor tracking every client PID/process group/start identity. Killing the
host Docker CLI does not prove psql/backend exit. On timeout or interruption,
stop all replay/ledger/copy, fail the lane, terminate only verified client groups
(TERM grace 5s, then KILL verification 5s), and shut down the entire owned cluster.
Ownership-check before exact-ID stop (10s), and again before kill or stopped-ID rm
if needed; each control call is bounded to 20s and total cleanup to 60s. Failure
to verify ownership, daemon identity/access, client/backend termination or resource
removal means INCOMPLETE, even if a later disappearance is observed.

Finally cleanup applies after success and every failure, including failed bootstrap.
Ownership proof authorizes cleanup even if storage/bootstrap validation failed.
Require independent same-engine healthy inspect absence, a separate successful
full-ID-filtered absence query and correlated die/destroy or independently reviewed
equivalent runtime-removal evidence. A generic inspect error, stop response or elapsed
timeout is insufficient. Before-inspect must prove only container-managed tmpfs/scratch
resources; independent runtime-removal evidence must establish their release.
Missing events or unavailable release evidence means INCOMPLETE. This proves no
physical memory erasure or Docker Desktop VM swap property. Never resolve cleanup
by name, enumerate project targets, prune Docker, delete host storage or stop an
unrelated database. Retain only reviewed sanitized source/catalog/outcome evidence
in the workspace for operator resolution, never credentials.

Before later execution authorization: review exact package/source bytes; supply
the image digest and verify local prerequisites in that separately authorized
stage; approve a dedicated runtime adapter and its mocked safety tests; accept
the bootstrap/Auth/ledger assumptions; approve the synthetic-only matrix scope;
and review any executable successor derivative independently. Compatibility
decisions in the matrix remain open. An owner may separately authorize bounded
exploratory negative tests while acceptance outcomes remain blocked; neither
local results nor removed review stops close B01-B07 or approve deployment.

Unresolved prerequisites: B01 credential/claim/BYPASSRLS compatibility; B02 future
service/helper grants and direct-write consumers; B03 actual creators and global
default effects; B04 deployed catalog/ledger/byte provenance; B05 SC-06/SC-07 order,
legacy four/seven-argument consumers and organization-admin disposition; B06
provider uncertainty, retention/reset/revocation and external consumers; B07
exact-byte approvals and environment readiness. OD01/03/04/09/12/13/14/16/17/18
remain open. Image/extension/startup/supervisor availability is UNVERIFIED.
Separate psql sessions, migration transaction wrappers, ledger post-commit behavior
and the specified expected-error subtransactions need adapter implementation review; no outer -1 wrapper
around B05/full chain is accepted. Independently review and authorize any stopped-
successor derivative, including a COMMIT variant needed for cross-session S tests.
The originals and this validation copy retain both stops and final ROLLBACK.

Stage 1.10 refines the non-executable matrix with T1 single-statement expected-error
capture, T2 whole-file refusal, T3 committed/concurrent steps, per-case cleanup C
and incomplete-run rule A. Those specifications resolve preparation ambiguities;
they do not prove PostgreSQL behavior or supply executable wrappers. Every M01–M21
remains NOT RUN. A failed assertion must produce an INCOMPLETE acceptance report
and nonzero future-run status, even if resource cleanup is separately FAILED_CLEANED.
The Stage 1.9 report/hash evidence is preserved as the entry baseline; changed
package pins are recomputed in Stage 1.10 evidence, never retrospectively rewritten
in Stage 1.9. The manifest is consistency evidence and must be separately approved.

## Exact runtime prerequisite contract — UNRESOLVED / NOT RUN

The versions below are inherited requirements from the pinned bootstrap/Stage 1.9
contract, not new selections, available installations or an approved combination.
All NULL identities in runner_contract.json must remain unresolved until independent
evidence and owner approval supplies exact bytes. No Docker CLI/version/info/inspect
or service probe was performed during remediation. None of the future identity
verification steps here is authorized to run by this document.

| Component | Existing required version or version status | Immutable identity/evidence to approve | Future verification, after separate authorization |
| --- | --- | --- | --- |
| Local image | Reference only public.ecr.aws/supabase/postgres:17.6.1.166; linux/amd64 | repository@sha256, content image sha256 ID, architecture/OS, image config/layer provenance, entrypoint and all required file inventory; pins NULL | Pinned CLI explicit endpoint, private config, local inspect with no pull; digest resolves to exact content ID/platform; inspect approved initializer-free startup capability. Missing image refuses, no download/build/substitution |
| Docker CLI | Exact version UNRESOLVED | Absolute checked local non-reparse executable, raw SHA-256/length, version/build provenance and dependent executable/DLL inventory | File hash before every invocation, exact argv, no PATH/shell/plugin/helper; separately bound version output. Version text alone never substitutes for executable hash |
| Engine/Desktop/API | Exact versions UNRESOLVED | Approved engine ID, endpoint, Engine/API/Desktop versions/build identities, linux OS and version-specific metadata representations | Same explicit npipe:////./pipe/dockerDesktopLinuxEngine, healthy engine ID/version/API checks before create and every lifecycle/SQL/signal operation. Context desktop-linux is informational; identity change refuses and triggers ownership-safe incomplete handling |
| Runtime host/Python/config | Exact versions/builds UNRESOLVED | Trusted Windows build, Python executable/dependency hashes, adapter interpreter identity, private checked config bytes/absence, minimal approved environment keys, system/tool dependency inventory | Private stable input/config staging, rehash independently approved source manifest and tool bytes before use. No ambient credentials/environment dump or config/context lookup |
| PostgreSQL toolchain | server_version_num170006 (17.6) required; toolchain build UNRESOLVED | In-image initdb/postgres/psql/pg_ctl absolute paths, SHA-256/length, package/build provenance and linked libraries | Local approved image file inventory before startup; later socket-only server version/effective settings plus tool versions, each bound to approved bytes. No host psql or TCP fallback |
| vector / btree_gist | 0.8.0 / 1.7 required in extensions | Control, install/update SQL, shared libraries and dependencies hashes/lengths/provenance, exact package architecture; identities NULL | Approved image inventory must contain exact files and vector1536/cosine/HNSW dependencies; authorized bootstrap extversion/schema probe. No substitution/install/download/skipped migration |
| Startup shim | Version UNRESOLVED, artifact absent | Exact source/executable bytes, interpreter dependencies/hash, build identity and independent review | Reviewed bare initdb bypasses image initializers; inspected sole512MiB tmpfs owner/mode; drop root/capabilities; no network/host storage. Metadata and effective checks both required |
| In-container supervisor | Version UNRESOLVED, artifact absent | Exact bytes/interpreter/build/dependency identities, monotonic-deadline/signal/process-start proof and review | Mocked failure tests then separately authorized tracking of PID/group/start identity, bounded termination and full cluster shutdown; host CLI exit insufficient |
| Dedicated adapter and SQL probe/derivative artifacts | Version UNRESOLVED; runtime_adapter NULL | Exact adapter/input/probe/fault/barrier bytes, T1/T2/T3 wrapper design, derivative hash and stop/transaction changes, mocked safety evidence and independent approval | No adapter execution until all approved identities checked. Rollback S and COMMIT S require separate artifacts and approvals; unchanged copy remains stopped. No run-time stop stripping |
| Offline provider fake and independent evidence observer | Version UNRESOLVED, artifacts absent | Exact bytes, durable call/correlation/loss model, identity-free transcripts, cleanup observer/event/resource-release mechanism review | No real provider; fake Auth owner writes isolated and distinguished from RPC reachability; observer independently checks commit/rollback and resource absence/release. Mocks alone not engine evidence |
| Bootstrap/Auth/ledger/fixtures/chain | File versions fixed by manifest; 40 migrations | Raw bytes/hashes/lengths, synthetic shim compatibility acceptance, independently approved manifest identity | Validate exact set/order/version/name/path before create; rehash staged bytes before use; ledger records only completed files, never proves hashes on its own |

The image may not provide the declared versions or a safe startup/termination
environment; this remains unresolved. A changed version requires separately
supported contract/compatibility review, not silent selection during a run.
Approving file-only remediation does not approve component availability, engine
access, installation, execution, collection or deployment.

## B01–B07 decision register — ALL OPEN

An authorized project owner must be identified through project authority; no
person, assignment, approval, external caller or installed/deployed state is
asserted here. Existing source evidence narrows each question but cannot answer
the external-state or compatibility parts. E23 read-only authorization is a draft,
not permission to collect. These rows preserve the earlier blocker meanings.

| Blocker | Unresolved question | Required evidence | Compatibility and security consequences | Decision required from an authorized project owner | Safe source work before decision? |
| --- | --- | --- | --- | --- | --- |
| B01 | What authenticates service requests, human actors and synthetic scalar/JSON claims; what real role/BYPASSRLS/inherited/SET paths exist? | Authorized redacted D01–D03/K02 request-mode, backend mapping, gateway/role semantics, complete reachability; no secrets. Source traces alone don't attest gateway identity | False claim/actor trust could permit delegated grants or direct writes; changing role mode can break commands or RLS. Synthetic shim cannot certify real authentication | Accept exact request/actor/role boundary and tested claim mode, or authorize a supported change with compatibility scope | YES documentation, source inspection and synthetic oracles; NO real-role/grant/body changes or acceptance of shim as production proof |
| B02 | Which existing helpers/direct writes are intended public/service entries; should future service EXECUTE default remain? | Per-signature arg/default/return/owner/path/ACL grant contract, nested dependency/call sites and external-consumer attestation D04/K04/K06/K09; actual creators/defaults K03 | Revocation can break workers/RPC/trigger setup; retained defaults expose future helpers; table/column/view/RPC bridges bypass intended boundary | Approve explicit entry/helper/direct-write grants and future default disposition, with known consumer effects | YES inventory and mock/test specification; NO new grants/revokes, generic purpose registration or legacy retirement |
| B03 | Which identities actually create migrations/functions/extensions, and what global PUBLIC default changes affect other schemas/creators? | Authorized K03/K08 actual creator/SET ROLE provenance, global/per-schema ACLs, all schema/extension/procedure/aggregate consumers, baseline contracts | Global revoke affects new functions beyond public; public service default doesn't apply everywhere; wrong creator assumptions cause outage or unintended privilege | Accept exact creator/scope/default impact or authorize a reviewed alternative; decide cross-schema/extension compatibility | YES isolated probe designs/definition comparison; NO global/default changes beyond already stopped draft, no extension reinstall |
| B04 | Does any target match approved catalog, exact migration lineage and applied raw bytes? | Authorized K01/K04–K09 full definitions/owners/ACLs/policies/FKs/indexes/triggers/bridges plus independent applied-byte provenance and manifest approval; ledger version alone insufficient | Count/presence preflights can miss changed definitions; wrong history/owner invalidates both rollback and privilege assertions | Accept target-specific provenance/catalog completeness, or authorize investigation/reconciliation with exact scope | YES local hash/source comparison and preflight coverage limits; NO manufactured ledger rows, assumed deployed equivalence or external collection |
| B05 | What order for SC-06 body qualification and SC-07 schema/temp hardening; retain/guard/retire legacy assign4/create7/invite_approve7; allow organization-admin legacy approval? | Full source/deployed routine definitions and lookup/dependency analysis, external-call inventory/attestation, organization-admin product policy, authenticated actor flow and compatibility/security test proposal | assign4 can self-grant/overwrite scope; invite_approve7 trusts supplied decider without new guarded assignment; blind hardening breaks unqualified bodies; new path denies org-admin and rolls back decision | Separately authorize exact body/schema order and legacy signature/behavior disposition including org-admin. No automatic unconditional-failure replacement | YES document known outcomes and source-only new-path tests; NO altering legacy signatures/bodies/ACLs or assuming external consumers absent |
| B06 | Which direct/adjacent-audit/maintenance/provider/lifecycle/retention/revocation consumers must survive; how reconcile historical gaps/unknown provider work? | D04 consumer/maintenance attestations; provider evidence guarantees and correlation ownership; audit retention/reset requirements, cutover mapping/OD01/03/04/12/13/14/16/18 policy; source reset predicate and terminal state contracts | Reset already refuses B05 TRUNCATE guard in F/U; adjacent platform/security-event ledgers mutable; trusted service GUC/direct writes can bypass RPC stage checks; accepted recovery ignores grant/issuer revocation and expiry; deletion/reset can destroy evidence or duplicate provider work | Accept or authorize explicit consumer/reset/retention/cutover/reconciliation and accepted-recovery policy; no guessed provider rollback/delete/password reset | YES identify incompatibility/exposure and bounded synthetic scenarios; NO replacement reset, audit deletion, provider action or selected lease/recovery policy |
| B07 | Which exact bytes/scope/components and immutable runtime identities will be approved and available; can termination/removal/resource release be proved? | Complete runtime table above, all NULL pins resolved with independent provenance/review, approved derivatives/wrappers/fake/observer, mocked failure results and later separately authorized local availability/effective evidence | Mutable image/context/CLI, unsafe startup or untracked backend invalidates containment; missing cleanup proof makes run incomplete; source report isn't execution permission | Approve exact environment/component/input/probe identity and bounded run scope in a separate authorization. Reject availability gaps or seek supported revised contract | YES this documentation/hash remediation; NO execution adapter implementation, runtime probe/startup/SQL or treating tag/guard as approval |

Disposition for all seven: OPEN, evidence unavailable/uncollected, owner decision
UNRESOLVED. No blocker is closed by documentation, an offline hash match, successful
new overload, mocked result or time elapsed. Source preservation is intentional
until separately supported decisions authorize behavioral changes. The package
is ready for another source review, with runtime/compatibility blockers still open.
