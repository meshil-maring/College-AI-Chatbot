# B05 Stage 1.9 independent readiness review

2026-10-12, Asia/Calcutta. Source review and offline checks only.

**READINESS REVIEW FAIL — BLOCKERS REMAIN**

The revised package passes its nine offline unit checks and every declared raw-byte hash/length comparison. The fixture uniqueness repair agrees with the source index. Original containment stops, final rollbacks and existing runners are preserved. However, the runtime matrix still leaves several case-specific outcomes and transaction/error-handling methods unspecified, and the immutable environment pins and reviewed runtime components are unavailable. The package is suitable for continued preparation; it is not yet a complete, reviewable execution proposal.

This verdict does not require runtime tests to have passed during an offline review. Their **NOT RUN** status is correct. The findings distinguish preparation gaps from deliberately deferred environment, compatibility and authorization evidence. A separately authorized exploratory subset could document known failures without closing B01–B07, but its exact adapter, inputs, transaction methods and scope would still need review. This report grants no execution, collection, installation or deployment approval.

Reviewed all ten requested files in `scripts/validation/b05_containment/`, plus the source migration chain, original stopped drafts, existing guard, relevant maintenance SQL and existing B05 recovery/evidence contracts. No Docker/PostgreSQL startup, engine inspection, database/provider connection, SQL/migration/harness execution, runtime case, secret/environment-credential inspection, executor implementation, executable SQL derivative, deployment or push occurred. Unit tests import preparation definitions but do not call `main()` or `preparation_plan()`.

**Findings, ranked by severity**

1. **High — Expected-error continuation inside the S transaction is not specified.** [M06](../../../scripts/validation/b05_containment/test_matrix.md#L18) requires behavioral probes inside the successor transaction using savepoints; [M15](../../../scripts/validation/b05_containment/test_matrix.md#L63) similarly requires rollback of individual mutation probes. [README:101](../../../scripts/validation/b05_containment/README.md#L101) and [contract:135](../../../scripts/validation/b05_containment/runner_contract.json#L135) require `psql -X` and `ON_ERROR_STOP=1`. A savepoint makes recovery possible on the server, but alone does not prevent the client from exiting at the expected error before issuing recovery or subsequent assertions. The README explicitly defers this method to adapter review at [line 197](../../../scripts/validation/b05_containment/README.md#L197). Specify and independently review how the expected SQLSTATE is captured, the failed statement is recovered, later probes remain inside the intended containment transaction, and unexpected errors still fail closed. A connection-close rollback is suitable for refusal tests; it cannot establish that remaining S probes or postflight ran. No adapter was implemented here.

2. **High — Several matrix cases are scenario inventories rather than complete acceptance oracles.** [M09–M13](../../../scripts/validation/b05_containment/test_matrix.md#L21) enumerate overload, identity, expiry, transition and concurrency scenarios without binding every subcase to its synthetic setup, exact entry identity/arguments and permitted return/error outcome. M13's “one logical winning result” does not identify each participant's result and event delta for each ordering. M09 identifies retained legacy blockers but omits concrete self-assignment/scope-overwrite observations that would prevent a passing new overload from masking them. M11's finalization-after-expiry needs an explicit short-lived generation and controlled release before the five-second lock timeout and 120-second process deadline; the supplied invited fixtures expire seven days after their anchor ([fixture:85](../../../scripts/validation/b05_containment/fixtures_pre_b05.sql#L85)). Without that setup, a lock timeout could be mistaken for the required final decision-time expiry rejection. The source distinguishes NULL returns from `23514` and other errors ([B05:345](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L345), [B05:397](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L397)). Expand the affected subcases in the non-executable matrix. The row-by-row assessment below records the narrower gaps; it does not prescribe SQL to execute.

3. **High — Immutable runtime identity and independently reviewed startup/termination components remain unavailable.** The endpoint string is explicit, but [image digest/content ID:179](../../../scripts/validation/b05_containment/runner_contract.json#L179), [CLI path/hash and engine ID:195](../../../scripts/validation/b05_containment/runner_contract.json#L195), [startup shim:132](../../../scripts/validation/b05_containment/runner_contract.json#L132), [supervisor:213](../../../scripts/validation/b05_containment/runner_contract.json#L213) and [runtime adapter:8](../../../scripts/validation/b05_containment/runner_contract.json#L8) are NULL. The fail-closed requirements are an improvement, not an observed implementation. No available artifact proves the exact image can support bare initdb, the specified binaries/extensions, root-to-postgres capability drop, bounded in-container termination or independent resource-release evidence. Supply separately reviewed identities and component bytes, then obtain any environment verification under separate authorization. A reference tag and existing guard cannot fill these fields.

4. **High — Retained legacy authorization compatibility remains a hard acceptance blocker.** [B05:104](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L104) adds the guarded five-argument assignment while retaining the older four-argument identity. The latter's actor-equals-target bypass and conflict-update behavior remain in [Phase 8.1:430](../../../supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql#L430) and [line 469](../../../supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql#L469), with service EXECUTE at line 494. The seven-argument [legacy invitation approval:103](../../../supabase/migrations/20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql#L103) still trusts its supplied decider and calls the seven-argument creator at line 150. The successor deliberately retains these command grants ([successor:456](../../../scripts/validation/b05_containment/containment_successor.validation.sql#L456)); it does not replace their bodies. Organization-admin approval disposition and external-consumer evidence remain unresolved. This is a preserved source gap, not a new path-safety regression, and must remain separate from positive new-path results.

5. **Medium — Hash-drift rejection and SQL preflight rejection need separate M07 oracles.** [M07:19](../../../scripts/validation/b05_containment/test_matrix.md#L19) includes wrong source hash alongside SQL catalog/ledger tampering. The [ledger schema:54](../../../scripts/validation/b05_containment/bootstrap.sql#L54) has no hash column; the successor checks the version array and explicitly requires external byte evidence ([successor:78](../../../scripts/validation/b05_containment/containment_successor.validation.sql#L78)). Hash drift must fail the adapter's approved-input gate before SQL, with no ledger or SQL changes. SQL catalog/ledger variants instead need their expected failing statement/error and rollback comparison. The matrix currently does not bind these distinct failures to distinct observation stages. Do not claim the SQL preflight itself attests source bytes.

6. **Medium — Maintenance compatibility already changes in F/U after B05, before S.** The existing [reset preflight:38](../../../scripts/maintenance/reset_supabase_data.sql#L38) refuses any noninternal public TRUNCATE trigger. B05 already declares `trg_b05_lifecycle_no_truncate` on its lifecycle audit table at [line 890](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L890). Thus the reset trigger predicate would reject a successfully replayed B05 catalog even without the successor's additional admin-audit guard ([successor:352](../../../scripts/validation/b05_containment/containment_successor.validation.sql#L352)), assuming earlier reset prerequisites were met. M15 documents audit mutation behavior but does not explicitly assert this maintenance refusal. Carry this consequence into B06 acceptance and consumer/retention disposition; do not infer an approved replacement reset method. No reset was run and no installed guard is claimed.

**Reproduced offline checks**

From `F:/Git Project/CollegeAIChatbot`, the exact unit command was:

```powershell
python -B -m unittest discover -s scripts/validation/b05_containment -p test_preparation_safety.py -v
```

Exit 0; **9 tests passed**, reported in 0.195 seconds. These are eight path tests plus one fixture test, not nine runtime cases:

| Test method | Source line | Result |
| --- | --- | --- |
| `test_external_and_ambiguous_paths_are_denied_before_metadata_access` | test_preparation_safety.py:14 | PASS |
| `test_component_walk_stops_before_traversing_reparse_target` | :31 | PASS |
| `test_symlink_is_denied_even_without_windows_attribute` | :51 | PASS |
| `test_checked_regular_file_and_directory_do_not_resolve` | :57 | PASS |
| `test_non_directory_ancestor_and_non_regular_file_are_denied` | :72 | PASS |
| `test_missing_local_component_fails_without_resolution` | :84 | PASS |
| `test_remote_unknown_and_removable_drive_types_fail_before_lstat` | :91 | PASS |
| `test_unc_or_drive_relative_repository_is_denied_before_windows_api` | :101 | PASS |
| `test_pending_emails_are_unique_and_staff_has_matching_synthetic_identity` | :112 | PASS |

Inspection agrees with the tests: syntax rejection precedes the drive API and metadata access ([prepare:35](../../../scripts/validation/b05_containment/prepare.py#L35)); Windows local fixed/RAM classification precedes lstat (line 47); component lstat rejects symlinks/reparse attributes before descending (line 64), and directories/files must have the appropriate type. No unchecked `resolve()` is used. The explicit input set is checked at lines 94–98 and file hashes/lengths at lines 112–115. The AST contains only `__future__`, argparse, hashlib, json, os, re, stat, pathlib and ctypes imports; direct inspection found no executor or environment/credential loading.

The tests use mocked filesystem/API results, including reparse points at the root, repository, directory and final file. They establish code ordering under those mocks, not kernel enforcement against concurrent path replacement. They do not exercise `preparation_plan()`, real mapped drives/junctions, private runtime staging or Docker targeting. The stable-checkout/trusted-runtime limitation and future independent manifest approval are correctly stated at [README:23](../../../scripts/validation/b05_containment/README.md#L23). No blocking defect was found in the reviewed lexical path gate within that stated scope.

**Fixture uniqueness against source**

The actual pending unique index is [Phase 7.17:135](../../../supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql#L135): `(institution_id, lower(email)) WHERE status='invited'`. It has no role key. All seven pre-fixture institution invitations use tenant A; the four invited emails are `existing-a`, `new-account`, `staff-recipient`, and `faculty-recipient`, each suffixed `@example.invalid` ([fixture:79](../../../scripts/validation/b05_containment/fixtures_pre_b05.sql#L79)). These are distinct lowercase keys. Invitation suffix 6 maps to confirmed Auth/public user suffix 12, approved staff request suffix 6, and no pre-existing role grant; suffix 1 still uses existing-a. The fixture test's uniqueness check over labels is valid here because tenant and domain are constant; it is not a general SQL constraint validator.

Also checked the invitation table PK/token uniqueness, normalized email and lifecycle constraints in [Phase 7.14:28](../../../supabase/migrations/20261001020000_phase_7_14_super_admin_university_admin_lifecycle.sql#L28); the global platform invited-email index at [Phase 9:31](../../../supabase/migrations/20261008000000_phase_9_super_admin_invitations.sql#L31); and B05's unique operation key at [line 30](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L30). Post-fixture stage emails are distinct from the pre-fixture emails. Snapshot Auth/public/operation namespaces remain separate, and their owner inserts are explicitly not RPC-reachability evidence ([post-fixture:1](../../../scripts/validation/b05_containment/fixtures_post_b05.sql#L1)). The uniqueness repair is **verified in source**; successful fixture SQL loading is **NOT RUN**.

**Hashes, ordering and preservation**

Full independently recomputed paths, SHA-256 values, lengths, comparison results, stop lines and transaction markers are retained in [B05_STAGE_1_9_OFFLINE_HASH_EVIDENCE.json](B05_STAGE_1_9_OFFLINE_HASH_EVIDENCE.json). Computation used `Path.read_bytes()` and `hashlib.sha256(raw)`, without newline normalization or calls into the preparation plan.

| Inventory check | Result |
| --- | --- |
| Migrations | 40/40 SHA-256 and byte lengths MATCH |
| Other pinned inputs | 12/12 SHA-256 and byte lengths MATCH |
| Migration directory versus manifest | Exact sorted 40-file set; no missing/extra SQL file |
| Orders, versions, names and paths | Orders 1–40; unique ascending 14-digit versions; filename/version/name/path mappings MATCH |
| Last migration | `20261017000000_b05_invitation_acceptance_security.sql`, 53,941 bytes; SHA-256 `581146602e75d94342777b81ee70b9ab423fb0117b2fda8b871d4b750249bc1e` |
| Manifest itself | 24,714 raw bytes; SHA-256 `f08d5a4f990e051fa952994bcad01628107e67c064530b7edd429ed0d431cc35` |
| Original candidate | 49,694 bytes; SHA-256 `897a4c786adc487bce04462690f8a4bbcab215f2e3e53841f84a82f40c1a63c7` |
| Successor source and validation copy | Byte-identical, each 51,805 bytes; SHA-256 `d360dd302c7be96e042d45d3056bd15934b107ab8c8de8ada9c113d2b8344d37` |
| Existing shared guard | 8,322 bytes; SHA-256 `2a7617a5f0771712fe816ff5dfe3b922e7294ab11553f45fc6bac5364bd5fcbe` |
| Successor ledger array | Matches all 40 manifest versions exactly |
| Audit expectations | Original 11-column check retained; successor 12-column/decision_key check retained |

The original candidate has unconditional review/dependency exceptions at lines **28/31** and final `ROLLBACK;` at **443**. The original successor and identical validation copy have them at **42/45**, with `BEGIN;` at 39 and final `ROLLBACK;` at **475**. The exception bodies remain active, not commented markers. All successor pre/postconditions remain because the copy is byte-identical. No derivative was created. The copy is outside the migration directory and its manifest ledger version is NULL.

These exact preservation commands returned no tracked differences (exit 0 for the diff commands):

```powershell
git status --short
git diff --no-ext-diff --no-textconv --exit-code HEAD -- scripts/validation docs/reviews/student_enrollment_final_2026-10-11/SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql docs/reviews/student_enrollment_final_2026-10-11/SECURITY_CONTAINMENT_POST_B05_SUCCESSOR_DRAFT.sql supabase/migrations
git diff --check
```

At entry, `git status --short` showed only the existing untracked `scripts/validation/b05_containment/` package. The review adds only this report and its hash evidence. Existing tracked runners, purpose allowlist, drafts and migrations are unchanged relative to HEAD; the package's pinned bytes also remain unchanged. Git warned that the user-global ignore file was inaccessible; it was not inspected or changed. This is bounded Git/source preservation evidence, not an inventory of every ignored file or a claim about historical executions.

**Runner contract and environment evidence**

| Requirement reviewed | Source specification | Available evidence/status |
| --- | --- | --- |
| Immutable image | repository digest plus content image ID, linux/amd64, pull=never, local absence/mismatch refusal; contract:177 | Requirements explicit; both approved pins NULL; availability UNVERIFIED |
| CLI/endpoint/engine | absolute CLI/hash, explicit local named pipe/private config, no mutable context selection, approved engine ID/rechecks; contract:192 | Endpoint fixed in source; CLI/hash/engine ID NULL; actual endpoint/engine unavailable |
| Startup isolation | fresh bare initdb; no image initializers/TCP/network/ports/host storage; sole hardened 512 MiB PGDATA/socket tmpfs; private namespaces; root drop and zero postgres capabilities; contract:10/110 | Detailed specification; metadata/runtime representations and startup shim unreviewed/unavailable |
| Target ownership | fresh token/full ID, exact name/purpose/image labels, create-before-start, bounded provenance recovery via exclusive cidfile/event; contract:70 | Explicit fail-closed design; no implementation or engine evidence |
| Process termination | monotonic deadline; verified in-container PID/group/start identities; TERM 5s/KILL verification 5s; owned cluster shutdown; contract:138/212 | Correctly distinguishes host CLI exit from backend exit; supervisor NULL; enforcement UNVERIFIED |
| Cleanup | finally on every outcome; ownership-only exact-ID stop/kill/rm; control call 20s/total 60s; independent healthy inspect absence + separate ID-filtered absence + correlated removal/resource evidence; contract:221 | Explicit independent evidence requirement; actual event/release mechanism and auto-removal races unverified; missing evidence means INCOMPLETE |
| SQL client | postgres OS user, explicit socket/db/user, -X, ON_ERROR_STOP, no host/DSN/TCP fallback; contract:135 | Specification only; expected-error continuation gap remains |
| Exact engine/dependencies | server_version_num 170006, vector 0.8.0, btree_gist 1.7; bootstrap:9/30 | Declared requirements, no image/binary/control/SQL/shared-library evidence; UNRESOLVED |
| Auth/ledger | synthetic roles/claims/Auth rows and empty local ledger; bootstrap:23/33/40/54 | Source shape available; real gateway/JWT/provider and Supabase migration tooling equivalence UNRESOLVED |

Source demonstrates the need for `extensions.vector(1536)` and its cosine HNSW operator class ([embedding migration:14](../../../supabase/migrations/20250718000000_phase_3_6_embeddings.sql#L14), [index migration:14](../../../supabase/migrations/20260905000000_phase_3_7_1_vector_search_index.sql#L14)) and btree_gist ([faculty migration:178](../../../supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql#L178)). It does not demonstrate those components are installed in the proposed image. No local image manifest, extension binaries, startup script, supervisor or independently collected engine record was supplied. No downloads, host binary discovery, Docker calls or external compatibility assumptions were used to fill that gap.

The old guard's tag/context and purpose checks are source reference only: [disposable_container.py:13](../../../scripts/validation/disposable_container.py#L13) excludes the B05 purpose, and line 26 uses a mutable context. It must not be represented as implementing this newer contract or reused through a borrowed purpose. Named-pipe labels/token provenance also do not isolate this task from a hostile daemon administrator; the package correctly states that trust limit.

**All 21 runtime cases — NOT RUN**

The matrix has exactly M01–M21, each once and in order, all ending **NOT RUN**. F/U/S/N lane definitions supply shared setup, while fixture mapping, audit tables, provider-state tables and M21 fault tables refine selected cases. **C** below denotes the shared cleanup oracle: final cleanup for every created lane; verified exact-ID/resource absence and termination; `FAILED_CLEANED` only for a verified failure with cleanup; `INCOMPLETE` for missing ownership/daemon/termination/removal evidence. Pre-create denial requires zero created resource/SQL. C is specified by README:56/168 and contract:221/240; it has never been observed. A per-probe rollback does not replace C.

| ID / source line | Setup and action reviewed | Expected-result / audit oracle reviewed; remaining specificity gap | Cleanup / status |
| --- | --- | --- | --- |
| M01 / 13 | F bootstrap, exact 40-file replay | Versions/schema/owners/hash/order and post-success ledger required. “Catalog agrees with source” needs the finite comparison coverage and comparator approved with the adapter; audit is baseline capture, not a grant/event success assertion. | C; NOT RUN |
| M02 / 14 | U pre-B05 legacy rows, replay B05 | Preserve old IDs/status/grants/history; added fields NULL on legacy rows, no fabricated operations. Need explicit pre-40 snapshot timing and scoped legacy-row comparison rather than an after-post-fixture global NULL assertion. | C; NOT RUN |
| M03 / 15 | Fresh 39 baseline, approved pre-COMMIT failure derivative or cancellation | Compare DDL/ACL/defaults/rows to 39 baseline; no version 40, no committed audit changes. Each injection needs the exact point and client outcome; cancellation before COMMIT must be distinguished from lost response after COMMIT. | C; NOT RUN |
| M04 / 16 | Pause B05 before commit; independent client sessions | No intermediate default exposure; final ACL comparison. Pin which new identities and replaced old identities are probed: an old committed callable is not proof of a new uncommitted exposure. Reapply subcase lacks a precise error/state/ledger oracle. | C; NOT RUN |
| M05 / 17 | Stopped copy and independently approved first-stop-only negative derivative | First/second unconditional error, disconnect rollback, unchanged data/catalog, no successor ledger row. Expected exception SQLSTATE is P0001 by source; derivative unavailable. | C; NOT RUN |
| M06 / 18 | Approved S transaction with internal probes; separate approved COMMIT derivative for concurrent S | Preserve pre/postconditions and rollback baseline, including rows/audits. Neither derivative exists. Expected-error capture/continuation remains unspecified (finding 1). | C after transaction rollback; NOT RUN |
| M07 / 19 | Independent tamper variants, final post-mutation injected failure | Fail closed and roll back all changes. Specify expected statement/SQLSTATE per variant; hash rejection is an external pre-SQL gate, not a ledger SQL predicate (finding 5). | C; NOT RUN |
| M08 / 20 | Real SET ROLE/claims, every targeted table/private table, columns/sequences/bridges | S client 42501 and effective privileges false; private-table service SELECT-only; source-specific MAINTAIN assertions explicit. Needs concrete service positive controls and view/RPC/sequence bridge probes rather than blanket retained-service assumptions. Audit mutation deltas use M15 table. | C; NOT RUN |
| M09 / 21 | Enumerate all overloads/helpers; direct/nested calls by client/service | New client/private-helper denials explicit. Add case-specific legacy actor-equals-target/scope-transfer outcomes and audit changes; enumerate authorized nested positive calls with their identity/inputs. Known legacy success must remain a blocker. | C; NOT RUN |
| M10 / 22 | Correct principal/recipient/tenant plus inactive/revoked/forged/conflicting variants | No partial writes and guarded organization-admin denial required. Bind each variant to exact call and NULL/structured conflict/SQLSTATE outcome; audit delta zero on rejected mutations. Desired organization-admin compatibility still BLOCKED. | C; NOT RUN |
| M11 / 23 | Both kinds, token/rotation/expiry and target-lock wait | Current-digest checks and final expiry rollback required, with grant/audit delta zero. Needs short-expiry setup, barrier release within lock deadline, and explicit 23514 for final decision-time expiry versus earlier NULL rejection or timeout. | C; NOT RUN |
| M12 / 24 | Direct writers/resend/cancel/expiry with enabled guards, forged local settings | Immutable/terminal/reservation constraints and trigger bindings stated. Specify each transition's setup/entry/error, expected outbox changes and lifecycle audit attribution/deltas; local settings alone are not authentication. | C; NOT RUN |
| M13 / 25 | Separate clients, explicit row-lock barriers, both-order races | Stable operation/exactly-once audit/no foreign overwrite stated. Missing per-order participant outcomes, named release points and exact audit/event deltas; a generic timeout is not evidence of the required winner semantics. | C including every client; NOT RUN |
| M14 / 26 | Fresh eligible commands with BEFORE INSERT P0001 faults on four audit tables | Full SQL state/grant/audit rollback, no success; independently durable fake account retained. Expanded rows 80–95 supply deltas. Bind fault table to each command's actual insertion path and verify a successful control would reach it. | Fault setup rollback or lane destruction, then C; NOT RUN |
| M15 / 27 | Populated audit tables, service and owner mutation probes with guards | Explicit F/U versus S per-table UPDATE/DELETE/TRUNCATE outcomes and attribution/deltas at 66–95. This correctly records unguarded adjacent ledgers as exposure. Expected-error continuation and reset-regression disposition remain open. | Per-probe rollback plus C; NOT RUN |
| M16 / 28 | Both new-account kinds; real operation/provisioning RPC transitions | Detailed boundary IDs/stages/Auth confirmation/grant/audit persistence at 99–115; source-only snapshots explicitly excluded as transition proof. Pin precise RPC/commit interruption points and fake-provider implementation bytes later. | C; NOT RUN |
| M17 / 29 | Both kinds, isolated durable fake create with lost/no-ID/ID-write response | One fake Auth account/create; frozen unknown operation; no reset/delete/blind retry; correlated-ID advance and SQL state invariants explicit. Fake correlation and loss injection need a reviewed adapter; real provider semantics excluded. | C; NOT RUN |
| M18 / 30 | Both accepted/confirmed kinds, canonical IDs and wrong/revoked variants | Confirmation-only accepted retry, no work for confirmed retry, no password; stable grant/audit/operation IDs. Specify each rejection's return outcome and synthetic revocation setup; accepted retention/deadline policy still unresolved. | C; NOT RUN |
| M19 / 31 | Immediate/legacy staff/faculty and separate student RPC; retry/conflict/grant failures | Expanded membership/student event-key and grant deltas at 91–92; preserve rejection grants and repair missing events. Pin each command identity and exact identical/changed retry result; N03 confirmation-readiness checks remain explicitly outside this SQL evidence. | C; NOT RUN |
| M20 / 32 | Transactional postgres probes in public/separate schema; other creator and dependency probes | Global PUBLIC/client default removal versus retained service default stated. Other creator/permissions/default profile and concrete vector/helper positive probes unspecified; no extension reinstall approval exists. | Roll probes back then C; NOT RUN |
| M21 / 33 | Future reviewed adapter mocks, denial/failure/loss/timeout/cleanup injections | Detailed fault oracles at 119–132; zero database access on denial; ownership-only cleanup; loss/daemon/client/removal failures INCOMPLETE. No adapter, mocks or engine results exist. Preparation units do not satisfy this case. | Explicit C/refusal/INCOMPLETE assertions; NOT RUN |

The shared audit oracle explicitly sets unlisted SQL-command audit-table deltas to zero and separates backend/fake auth-security-event recording from SQL-generated events (matrix:80–95). It correctly distinguishes baseline admin-audit TRUNCATE exposure from S denial and unguarded platform/security-event audits from the protected lifecycle ledger. These are useful source-derived expectations; they do not supply the missing method/ordering/entry outcomes above, and none is a runtime PASS.

**Transactions, ledger, partial failure and recovery**

Bootstrap and both fixture files have their own BEGIN/COMMIT. Among source migrations, explicit file wrappers occur only at manifest orders **33, 36, 38, 39 and 40**; all agree with `file_transaction`. B05's BEGIN at line 9 and COMMIT at line 995 encompass its new objects, replacements, trigger bindings and ACL changes. Most earlier migrations have no explicit whole-file transaction, so a later statement failure can leave earlier statements committed. `ON_ERROR_STOP=1` alone does not make those files atomic.

The proposed adapter must stop replay and destroy the failed fresh lane after any partial migration failure; no ledger entry may be written for a file whose completion is unverified. M21 describes this destroy/no-retry outcome. Do not characterize every migration failure as an atomic rollback. Do not wrap B05 or the entire chain in `--single-transaction`, which would conflict with internal COMMIT boundaries. Independent sessions prevent the baseline's disabled timeouts/check_function_bodies/row_security settings from leaking to later files; the external deadline remains necessary because the original baseline clears those settings ([baseline:16](../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L16)).

The ledger starts empty and requires one version/name/original-statements entry only after successful completion, plus separate raw-byte evidence. It is not prepopulated; it does not record the successor; a version row alone does not prove applied bytes. The method for retaining original statements, recording verified completion, and surviving response-loss boundaries has not been implemented or independently reviewed. B05 commits before the later ledger insert: ledger failure or ambiguous completion cannot undo that schema commit. The required recovery is fail/destroy that lane and start fresh, not retry or fabricate ledger state on the same cluster ([README:92](../../../scripts/validation/b05_containment/README.md#L92), matrix:128).

M03's pre-COMMIT failure lane must show baseline equality and no version 40. It must be separate from after-COMMIT/ledger-failure recovery. S retains an outer BEGIN/ROLLBACK; cross-session tests cannot see its uncommitted containment state and therefore need a separately reviewed COMMIT variant. Both variants and expected-error handling remain unavailable. All transaction/ledger/rollback behavior described here is source-derived and **NOT RUN**.

**B01–B07 reassessment**

No blocker is closed. The owner-decision register describes proposed roles, not assigned people or attestations ([existing evidence-readiness report:13](SECURITY_CONTAINMENT_OWNER_DECISIONS_AND_EVIDENCE_READINESS.md#L13)); the open E23 annex is a draft with pending authorization, not approval. No external consumers, owners, approvals, credentials, deployed data or live catalog state are invented by this review.

| Blocker | Status | Unresolved compatibility, authorization and evidence gaps |
| --- | --- | --- |
| B01 | OPEN; synthetic source profile only | Actual credential-to-role/claims/secret-key/PostgREST mapping; service BYPASSRLS contract; verified human/Auth/public mapping; inherited/settable roles and effective RLS. Scalar/JSON synthetic claims and SET ROLE cannot authenticate a real backend request. |
| B02 | OPEN; proposed access scope available | Explicit future creator/service entry/helper/default/trigger grant contract; legitimate nested/direct-write/worker consumers; overload routing and effective grants; retained service defaults intentionally not removed. No external consumer absence is established. |
| B03 | OPEN; postgres-only lane specified | Actual object-creation roles/sessions/default ACLs; cross-schema/global PUBLIC default effects; extension/procedure/aggregate and other-creator consumers; approved creator/schema coverage. A postgres-only shim cannot establish deployed creator compatibility. |
| B04 | OPEN; repository byte inventory verified | Current target catalog/definitions/owners/RLS/ACL/column/default/index/trigger/role/view/RPC state, engine/extension/application/gateway versions, deployed ledger and independent applied-byte provenance. Local manifest consistency and synthetic ledger are not deployed evidence. |
| B05 | OPEN; known legacy gaps preserved | SC-06/SC-07 body/schema/lookup/authority hardening order; retained four-argument assignment and seven-argument legacy approval/creator decisions; organization-admin compatibility; deterministic cancellation/expiry/revocation/role-lock outcomes and all-writer contracts. Required runtime evidence absent. |
| B06 | OPEN; conditional reset incompatibility verified in source | Actual external consumers; audit mutation exposure/attribution acceptance; retention/reset/revocation/in-flight and existing-data reconciliation/cutover policy; real provider correlation/idempotency/timeout/recovery guarantees and unknown-outcome evidence. B05 itself adds a reset-refusing public TRUNCATE guard. |
| B07 | OPEN; preparation integrity verified | Exact independently accepted package/manifest and future derivative bytes; explicit scope/execution authorization; immutable image/CLI/engine approvals and locally verified availability; reviewed startup shim/supervisor/adapter/mock safety/expected-error/ledger/staging methods; independent cleanup evidence and future runtime acceptance. |

OD01/03/04/09/12/13/14/16/17/18 remain expressly open in this package; the earlier register's remaining OD/E obligations are not silently closed either. T01–T14 from the earlier containment reviews also remain **NOT RUN**; this review does not substitute M-case preparation for their broader integration/consumer requirements.

**Exact independent inventory/static verification command**

The following read-only command was used for final source/evidence consistency verification. It does not import the package or execute SQL. The evidence file was separately emitted from the same raw-byte inventory with all 52 per-file results and transaction/stop locations.

```powershell
@'
import ast, hashlib, json, re
from pathlib import Path
p = Path('scripts/validation/b05_containment')
m = json.loads((p/'migration_manifest.json').read_bytes())
entries = m['migrations'] + m['pinned_inputs']
assert len(m['migrations']) == 40 and len(m['pinned_inputs']) == 12
assert sorted(x.name for x in Path('supabase/migrations').glob('*.sql')) == [e['filename'] for e in m['migrations']]
versions = [e['version'] for e in m['migrations']]
assert len(set(versions)) == 40 and versions == sorted(versions)
for i,e in enumerate(m['migrations'],1):
    assert e['order'] == i and re.fullmatch(r'\d{14}_.+\.sql', e['filename'])
    assert e['version'] == e['filename'][:14] and e['migration_name'] == e['filename'][15:-4]
    assert e['path'] == 'supabase/migrations/' + e['filename']
for e in entries:
    raw = Path(e['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == e['sha256'] and len(raw) == e['bytes'], e['path']
assert Path(m['successor_source']).read_bytes() == Path(m['successor_validation_copy']).read_bytes()
sql = Path(m['successor_validation_copy']).read_bytes().decode('utf-8')
ledger = re.search(r'IS DISTINCT FROM ARRAY\[(.*?)\]::text\[\]', sql, re.S)
assert re.findall(r"'(\d{14})'", ledger.group(1)) == versions
for rel in (m['pinned_inputs'][0]['path'], m['successor_source'], m['successor_validation_copy']):
    text = Path(rel).read_bytes().decode('utf-8')
    assert "DO $review_stop$ BEGIN RAISE EXCEPTION" in text
    assert "DO $dependency_stop$ BEGIN RAISE EXCEPTION" in text
    assert text.rstrip().endswith('ROLLBACK;')
assert '<>12 THEN' in sql and "attname='decision_key'" in sql and "attnum=12" in sql
assert '<>11 THEN' in Path(m['pinned_inputs'][0]['path']).read_text(encoding='utf-8')
matrix = (p/'test_matrix.md').read_text(encoding='utf-8')
rows = [line for line in matrix.splitlines() if re.match(r'^\| M\d{2} \|', line)]
assert [re.match(r'^\| (M\d{2})',r).group(1) for r in rows] == ['M%02d'%i for i in range(1,22)]
assert all(r.endswith('| NOT RUN |') for r in rows)
tree = ast.parse((p/'prepare.py').read_text(encoding='utf-8'))
imports = [n.module if isinstance(n,ast.ImportFrom) else a.name for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom)) for a in (n.names if isinstance(n,ast.Import) else [None])]
assert not any(x and x.split('.')[0] in ('subprocess','socket','requests','urllib','psycopg','dotenv') for x in imports)
evidence = json.loads(Path('docs/reviews/student_enrollment_final_2026-10-11/B05_STAGE_1_9_OFFLINE_HASH_EVIDENCE.json').read_bytes())
assert evidence['manifest_sha256'] == hashlib.sha256((p/'migration_manifest.json').read_bytes()).hexdigest()
assert [(r['path'],r['sha256'],r['bytes']) for r in evidence['results']] == [(e['path'],e['sha256'],e['bytes']) for e in entries]
print('PASS: 52 raw hashes/lengths, migration identities/order, preserved stops, evidence consistency; M01-M21 NOT RUN')
'@ | python -B -
```

Exit 0. The final verdict remains **READINESS REVIEW FAIL — BLOCKERS REMAIN**. Complete the non-executable case/method specifications and supply independently reviewable runtime identities/components before presenting a bounded execution proposal. Any later approval must identify exact scope and bytes; this report is not that approval.
