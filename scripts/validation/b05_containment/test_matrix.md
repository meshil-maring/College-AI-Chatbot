# Stage 1.10 planned validation matrix — Stage 1.12 targeted oracles — every row NOT RUN

Execute only under later explicit authorization. No PASS/availability claim is
made here. F = fresh 40-file empty-chain lane; U = upgrade lane with pre-fixtures
after 39; S = independently approved executable successor derivative (currently
blocked); N = separate fresh negative/tamper lane. All lanes use synthetic data.
Collect statement boundaries, SQLSTATE, return values, before/after catalog and
row snapshots, decision/event counts, lock ordering and cleanup outcome. Do not
declare acceptance when an expected result is conditional or a blocker is found.

| ID | Lane / case | Required oracle and injection method | Decisions / limits | Status |
| --- | --- | --- | --- | --- |
| M01 | F: bootstrap and full 40-file replay | Exact filename/hash/order, postgres owners, exact 17.6 and extension versions/schema; all statements succeed before ledger entry. Catalog agrees with source; no skipped migration or inferred demo data. | Image/digest/library pins unverified; bootstrap/Auth/ledger shim approval required (B04/B07). | NOT RUN |
| M02 | U: populated legacy upgrade | Accepted rows without accepted user/operation, expired/cancelled missing events, approved request without grant/audit; preserve old IDs, status, grants and historical audit bytes. New B05 columns initially NULL; no invented reservation/provider proof. | OD18 cutover/reconciliation policy remains open. | NOT RUN |
| M03 | N: B05 injected rollback | Review a distinct B05 derivative inserting RAISE SQLSTATE P0001 immediately before its COMMIT, or cancel/disconnect before commit. Compare tables, columns, functions, triggers, ACL/defaults, rows and absent version 40 against the 39 baseline. Do not rely on an outer transaction around internal COMMIT. | Derivative exact bytes require approval; original migration remains unchanged. A failure after COMMIT is recovery, not rollback. | NOT RUN |
| M04 | F: transaction/publication boundary | Pause before B05 commit, use independent anon/authenticated sessions to probe new identities; no unrevoked intermediate default grants become visible. After commit compare final ACLs. Reapplying B05 to the same DB is a negative test, not assumed idempotent replay. | Source has explicit BEGIN/COMMIT; verify rather than infer. | NOT RUN |
| M05 | F/U: unchanged successor copy | ON_ERROR_STOP stops at first review stop; disconnect rolls back. For second-stop reachability use a separately reviewed negative derivative removing only the first stop. Originals/copy stay stopped; catalog and data unchanged; no successor ledger row. | S body cannot run with this package as authored. | NOT RUN |
| M06 | S/N: containment body and rollback | Approved stop replacements retain pre/postconditions and final ROLLBACK. Put behavioral probes inside that transaction, using SET LOCAL ROLE/RESET ROLE and savepoints, then compare full baseline after rollback. A second connection cannot see uncommitted containment: a separately approved COMMIT derivative is needed for post-containment concurrent sessions. | B01-B07; transaction form and exact derivative review required. | NOT RUN |
| M07 | N: successor pre/postflight fail closed | Separate input-hash refusal before SQL from catalog/ledger P0001 refusals at the identified preflight. One fresh variant per mutation; compare rollback to the already-tampered baseline, then destroy that lane. Inject final P0001 after default/ACL changes before rollback. Never synthesize ledger to satisfy preflight. See detailed M07 below. | SQL ledger has no hash column. Preserve failing source behavior as a finding. | NOT RUN |
| M08 | F/S: effective ACLs | For anon/authenticated, actual SET ROLE plus matching synthetic claims; SELECT/INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER/MAINTAIN and column/sequence grants on every successor table and B05 private table. Check PUBLIC, grant option, inherited/settable reachability, views and RPC bridges. Expected S client denial 42501 and has_table_privilege(...,'MAINTAIN')=false for every client-reachable role; S service admin_audit_log MAINTAIN=false and B05 operations/lifecycle MAINTAIN=false in F/U/S. Retained service privileges on other tables are baseline findings, not blanket denial. Service operations/lifecycle tables SELECT only, direct writes denied. VACUUM-like commands need a separately approved nontransactional lane; use catalog assertions within S rollback. | S intentionally retains service writes elsewhere; B01/B02/B06 direct-write/consumer acceptance unresolved. No superuser session counted as a role test. | NOT RUN |
| M09 | F/S: every overload and private helper | Enumerate pg_proc identities/arg names/defaults/result/owners/SECURITY DEFINER/search_path/ACLs. Probe all b05_* identities, assignment 4/5, creators 6/7, legacy invitation approval, immediate approval and renamed assignment original. Client denied on new B05 entries; service private-helper calls denied; authorized nested calls still work. | Legacy 4-arg assignment and 7-arg approval/creator are retained hard blockers, not assumed repaired. OD09 and external callers unresolved. | NOT RUN |
| M10 | F/S: real identity and role checks | Platform actor for admin/platform grant; live tenant admin for staff/faculty; verified actor public/Auth mapping; recipient email/ID, requested role and approved request from storage. Test inactive actor/role/tenant, revoked issuer, foreign tenant, wrong/missing claims, conflicting existing scope and forged inputs; no role/invitation/audit partial writes. | B01 claim-mode assumptions; organization-admin denial in 5-arg path must roll back, desired compatibility outcome remains BLOCKED. | NOT RUN |
| M11 | F/S: token generation and expiry | For both invitation kinds: wrong/stale digest, rotate-before-reserve and reserve-before-rotate, positive expiry, expired token, wrong recipient; reservation rechecks current digest under invitation lock. Hold a conflicting target lock past expiry: finalization must roll back grant/audit at final DB clock check. | OD03/OD04 deadline/abandonment policy not silently selected. Fixture anchor is supplied from DB clock once; use explicit row-lock barriers, not host-clock assumptions. | NOT RUN |
| M12 | F/S: invitation transition guards | Direct UPDATE/resend/cancel/expiry writers with triggers enabled: immutable identity; terminal state cannot reopen; accepted requires matching reservation; reserved generation immutable; expired link cannot rotate. Verify exact enabled trigger tgfoid/type and parent/child scope guards. Fake b05.acceptance_id/recovery_id alone must not be treated as authentication. | Trusted direct service writes/BYPASS remain a separate authority limitation. | NOT RUN |
| M13 | F/S: parallel requests | Separate psql processes and row-lock barriers for each ordering in detailed M13. Bind each participant's return/error, winning operation, grant scope and event delta. Lock timeout/deadlock never substitutes for a specified winner. | Provider-started ambiguity stays frozen. Desired cancellation/product winner semantics OD04/OD12 remain open beyond current source contract. | NOT RUN |
| M14 | F/S: audit failures | Fixture-only BEFORE INSERT triggers RAISE P0001 on admin_audit_log, platform_role_audit_log, platform_institution_audit_log and b05_invitation_lifecycle_audit in separate cases. Invoke grant/finalization, immediate/student/legacy approve/reject, cancel/expiry/repair. Full transactional state/grants/audit unchanged; no success response. Remove fault by rolling back setup or destroy lane. | Provider state is not rolled back by SQL. Never disable normal guards to make fault setup pass. | NOT RUN |
| M15 | F/S: audit immutability and attribution | UPDATE/DELETE/TRUNCATE as real service, then owner with guards enabled and populated synthetic rows. Use the explicit per-table F/U versus S oracle below: F/U admin_audit_log TRUNCATE is allowed; S rejects it. Do not assume platform/security-event audit tables have mutation guards. Issuer-for-expiry/backend_actor/repair_actor/unrecorded_initiator preserved; repeated terminal repair adds at most one authoritative event and never guesses an old projection. Check restrictive actor/tenant FKs. | OD14/OD16 audit/retention/reset acceptance open; superuser guard disabling is outside asserted protection. | NOT RUN |
| M16 | F/S: durable interruption recovery | For institution AND platform new-account invitations, both sides of reservation, provider-start CAS, provider-ID recording, public-user provisioning, grant/acceptance/audit and confirmed-state writes. Assert synthetic Auth/public identity and confirmation state at every boundary using the state oracle below. Lost response after commit resolves recorded state; failure before commit reattempts only eligible step. Private-state writes go through actual RPCs in transition lane, not snapshot inserts. | Use backend B05_RECOVERY_CONTRACT boundaries; source-only snapshots do not prove reachability. | NOT RUN |
| M17 | F/S + offline fake: provider uncertainty | No real provider calls. For BOTH invitation kinds, fake records synthetic create/confirm attempts and owner-only synthetic auth.users rows. Test create success with response lost, response missing ID, and ID-write response lost separately. Durable fake account may exist while operation Auth ID is NULL; leave provider_started frozen and assert create count remains one across retries. SQL rejects resetting/releasing uncertainty, reopening IDs or blind second create. Correlated synthetic ID permits guarded advance; never compensate by account deletion or password reset. | Provider guarantees, evidence ownership and unknown-outcome reconciliation OD13/B06 remain pending; this cannot validate GoTrue behavior. | NOT RUN |
| M18 | F/S + offline fake: accepted recovery | For BOTH invitation kinds, correct generation/new-account/Auth/public IDs and active email allow password-free recovery; wrong digest/kind/ID, existing-account operation and revoked/mismatched user fail. Accepted retry repeats only fake confirmation; confirmed retry does no provider work. Preserve operation/grant/audit IDs. | Retention/expiry/revocation after acceptance and credential policy OD01/OD13/OD16 need owner disposition. | NOT RUN |
| M19 | F/S: membership/student regression | Staff/faculty immediate approve atomically decision/grant/audit; reject grants nothing and preserves all existing grants/permission grants. Identical legacy actor/reason retry returns original decision; changed actor/reason or opposite terminal decision conflicts. Student uses separate RPC and student allowlist; role-scope conflict/audit failure rolls approval back. | Organization-admin legacy path remains blocked. Email-confirmation readiness N03/OD12 requires separate offline fake orchestration checks. | NOT RUN |
| M20 | S/N: defaults and consumers | Create transaction-local probe functions as postgres in public and a separate schema; check global PUBLIC default removal, public anon/auth default removal and retained service default. Check other creator baseline independently; extension/vector routines and retained helpers/trigger invocations still function. Roll probes back. | B02/B03/OD17: global cross-schema/default creator effects and future service grants unresolved; no extension reinstall assumed safe. | NOT RUN |
| M21 | Dedicated adapter mocked safety / cleanup | Before any later SQL lane, approve mock tests for remote contexts/endpoint, DOCKER_HOST, short ID/name alias/wrong token/purpose/image, persistent storage, bad PGDATA/tmpfs, network/ports/host bridge, manifest drift, bootstrap/ledger/copy/SQL/timeout failure. No database reached on denial; only proven run-owned ID cleaned. Use the explicit M21 failure assertions below for create-response loss, interruption, daemon loss, surviving in-container clients and cleanup deadlines. Removal/termination/evidence failure reports INCOMPLETE; host CLI exit is insufficient. | Runtime adapter absent; no mocked or engine tests have been run. Reuse guard protections without generic purpose registration. | NOT RUN |

Fixture map: organization namespace 10000000, tenants 20000000 (A=1, B=2,
inactive=3); users/Auth 30000000 (platform=1, admin A=2, admin B=3, org admin=4,
existing=5, foreign staff=6, pre-granted staff=7, inactive=8, student=9,
unconfirmed=10, faculty=11, independent staff recipient=12). Membership namespace
50000000 (approved staff request=6 binds user 12); invitation 60000000 suffix 6
uses staff-recipient@example.invalid, distinct from suffix 1 existing-a@example.invalid.
Pending uniqueness is institution + lower(email), independent of role. Pending student
51000000; institution/platform legacy invitations 60000000/61000000 and
synthetic pending outbox 63000000 (invalid ciphertext markers, never sent); historic
audits 70000000/71000000. All suffixes are decimal padded to 12 digits. Interruption
snapshots 21-26 use invitation 62000000, Auth 32000000, public user 33000000,
operation 80000000. Negative cases mutate/cloned synthetic rows in isolated lanes.

Remaining decisions: B01 actual credential/claims/BYPASSRLS; B02 explicit helpers,
future service defaults and direct-write consumers; B03 actual creators and
global default impact; B04 catalog/ledger/byte provenance; B05 SC-06/SC-07
body/schema-hardening order and legacy 4/7-argument paths; B06 external consumers,
retention/reset/lifecycle and provider uncertainty; B07 exact approval and
environment readiness. OD01/03/04/09/12/13/14/16/17/18 (and the earlier review's
other owner decisions) are not closed by this preparation. Tests documenting
known legacy gaps must remain blockers even if the new paths pass.

## Explicit M14/M15 audit oracles — NOT RUN

F/U are the source baseline after B05; S changes ACL/defaults and adds the
admin-audit TRUNCATE guard, without replacing B05 bodies. These are source-derived
expected assertions for isolated populated lanes, not runtime observations. A
successor preflight failure remains a blocker. Never count a known baseline
exposure as containment acceptance. Each mutation probe is rolled back in its
own approved transaction/savepoint; no CASCADE or guard disabling.

| Audit table | F/U service and owner mutation oracle | S service and owner mutation oracle | Status |
| --- | --- | --- | --- |
| admin_audit_log | UPDATE/DELETE on populated rows raise 42501 through append-only guard. Service and owner TRUNCATE can succeed: known missing guard. | Service UPDATE/DELETE/TRUNCATE denied 42501 by ACL. Owner UPDATE/DELETE denied by row guard and TRUNCATE denied by new statement guard, 42501. | NOT RUN |
| b05_invitation_lifecycle_audit | Service SELECT only: UPDATE/DELETE/TRUNCATE/MAINTAIN privileges false. Owner populated UPDATE/DELETE and any TRUNCATE raise 42501 through B05 guards. | Same as F/U; verify triggers still enabled and bound exactly. | NOT RUN |
| platform_role_audit_log | Source service grants permit UPDATE/DELETE/TRUNCATE; no row/statement mutation guard is declared. Owner mutations can succeed. Record exposure, roll back. | Same source exposure; successor does not target this table. | NOT RUN |
| platform_institution_audit_log | Source service grants permit UPDATE/DELETE/TRUNCATE; no row/statement mutation guard is declared. Owner mutations can succeed. Record exposure, roll back. | Same source exposure; successor does not target this table. | NOT RUN |
| auth_security_events | Source service grants permit UPDATE/DELETE/TRUNCATE despite append-only description; no mutation guard is declared. Owner mutations can succeed. Record exposure, roll back. | Same source exposure; successor does not target this table. | NOT RUN |

The service mutation exposure includes historical postgres table defaults and
migration 32's broad service grants. Compare final effective ACLs first; unexpected
catalog differences fail the lane. S client MAINTAIN is false across every targeted
table and inherited/settable role. S service admin_audit_log MAINTAIN is false;
B05 private tables deny it in F/U/S. Do not infer other service MAINTAIN denials.

For SQL-command lanes, measure per-table row deltas from the captured baseline
and preserve existing audit IDs/bytes. All unlisted audit tables have delta zero.
Backend/fake-provider event recording is asserted separately, not mistaken for
SQL-generated auth_security_events. Expected deltas apply equally to F/U and S
when the approved source-compatible path can execute:

| Command / event | Required row and attribution assertions | Status |
| --- | --- | --- |
| New institution admin grant/finalization | admin_audit_log +1 role.assignment only if grant inserted; platform_institution_audit_log +2 verified/accepted events; lifecycle/platform-role/security-event deltas zero. Accepted retry adds zero to all. | NOT RUN |
| Institution staff/faculty finalization | admin_audit_log +1 role.assignment only if grant inserted; no admin-invitation projection, platform-role or lifecycle event. Retry adds zero. Approved matching stored membership and existing verified recipient required. | NOT RUN |
| Platform finalization | platform_role_audit_log +1 assign with actor_identifier super_admin_invitation:<invitation_id>, target identity and platform scope; other audit deltas zero. Accepted retry adds zero (do not replay the standalone legacy assignment routine). | NOT RUN |
| Immediate/legacy membership approval | admin_audit_log +1 role.assignment if grant inserted, plus exactly one membership:<request_id> decision event. Immediate action membership_request_approved; legacy action membership.approved. Identical retry adds zero if event exists, or repairs exactly one missing decision event without overwriting decision/time/grants. Legacy approved-gap repair may insert its missing grant; immediate approved-gap returns invalid_state without writes. | NOT RUN |
| Membership rejection / student approval | Rejection: no grant changes and exactly one correlated membership decision event (membership_request_rejected or legacy membership.rejected). Student: one student:<student_id> student.approve event and one correct scoped role if absent. Retry adds zero if event exists or one missing correlated event. | NOT RUN |
| Fresh cancellation/expiry, both invitation kinds | lifecycle +1 per (kind,invitation_id,status), repaired=false; institution admin additionally platform_institution_audit_log +1 projection; institution staff/faculty and platform add no projection. Preserve backend_actor, issuer_for_expiry or unrecorded_initiator attribution as source dictates. | NOT RUN |
| Historical terminal repair, both kinds | Missing lifecycle event +1 repaired=true; existing event +0 and original bytes unchanged. Never invent an old platform_institution_audit_log projection. Explicit actor uses repair_actor; absent expiry actor uses issuer_for_expiry; absent cancellation actor uses unrecorded_initiator. | NOT RUN |
| Injected audit INSERT failure | P0001, no success result; all SQL operation/decision/grant/invitation/outbox/audit changes roll back. The independently durable fake Auth account remains if creation preceded SQL failure; never assert provider rollback or deletion. | NOT RUN |

## Explicit M16–M18 Auth/provider state oracles — NOT RUN

Repeat the NEW-account state machine for institution-admin AND platform
invitations using distinct example.invalid emails and synthetic UUIDs. Create the
fake's Auth row only as owner in the isolated auth.users shim; exercise public-user
provisioning and private operation writes through real RPCs. Do not substitute
post-fixture snapshot inserts for these transition assertions. Institution
staff/faculty uses an existing canonical Auth/public recipient and approved
request, with zero create/password work. Existing-account platform reservation
returns NULL and performs zero provider work.

| Boundary / fault | Expected state and retry assertions | Status |
| --- | --- | --- |
| reserved / provider_started before fake creation | No new Auth/public user or grant; new_account=true, operation identity stable, IDs NULL. Once provider_started committed, lost CAS response freezes even if fake create count is zero. | NOT RUN |
| Fake create succeeds, response lost or contains no ID | Exactly one unconfirmed synthetic Auth row and one recorded fake durable result, no public user/grant; operation remains provider_started with Auth ID NULL. Retry performs zero additional creates; no ID guessing, account deletion, lease release or password reset. | NOT RUN |
| Correlated ID recorded / ID-write response lost | approved fake evidence binds invitation/generation/email to same Auth UUID; provider_created records that UUID. Lost SQL response resolves the committed operation; before-commit failure leaves provider_started. No second Auth row/create. Missing/mismatched Auth row must not allow public provisioning; FK/mapping failure leaves stage/grants unchanged. | NOT RUN |
| public user_created / finalization | Exactly one public user linked to the existing synthetic Auth UUID and matching email. Until finalization, no role or accepted state; finalization commits correct grant/accepted IDs/audits together. Failure preserves independently committed Auth/public rows and leaves SQL decision unchanged. | NOT RUN |
| accepted / confirmation timeout | Correct canonical IDs and grant/audit IDs persist. Fake confirmation failure before durable confirmation leaves Auth email_confirmed_at NULL; durable confirmation with response lost may leave it non-NULL while operation remains accepted. Retry only confirms the same ID, never creates/deletes/resets a password. | NOT RUN |
| confirmed-state response lost / retry | Fake confirmation makes same Auth row email_confirmed_at non-NULL; committed confirmed operation resolves without any further provider work. Failed confirmation-state write leaves accepted and allows confirmation-only retry. IDs, grants and audit counts remain stable. | NOT RUN |

## Explicit M21 adapter fault oracles — NOT RUN

These describe required future mocks and separately authorized engine checks.
No adapter exists and none of these cases has run. Preparation unit checks in
`test_preparation_safety.py` do not satisfy M21.

| Injection | Required assertion | Status |
| --- | --- | --- |
| Missing image/digest/CLI/engine approval; image absent or wrong platform | Refuse before create; zero pulls/downloads, SQL or existing-container fallback. | NOT RUN |
| Context/config rebinding, Docker environment override, wrong engine; privilege/capability/device/shared namespace/network/port/mount/tmpfs drift | Exact endpoint/config/CLI pins and full metadata checks deny before database access. Recheck before every operation. Cleanup only a proven newly created full ID. | NOT RUN |
| Create succeeds but response/ID is lost or command reports failure | No start/SQL until independent fresh cidfile + same-engine create-event provenance and full-ID ownership agree. If unrecoverable, INCOMPLETE and no borrowed ID/name/enumeration/prune cleanup. Mock successful recovery and contradictory provenance separately. | NOT RUN |
| Bootstrap/fixture/migration/copy/ledger failure | Stop replay; failed or rolled-back migration gets no ledger row. After B05 COMMIT, ledger failure destroys lane, never retries cluster. FAILED_CLEANED only with independent removal/resource evidence; otherwise INCOMPLETE. | NOT RUN |
| Interrupt before/after create, during readiness, SQL/concurrency, signals or cleanup | Finally handler accounts for every recorded created resource and client; no later statements/ledger writes. Missing identity/termination/removal evidence => INCOMPLETE; no success from elapsed time. | NOT RUN |
| Host CLI timeout leaves in-container psql/backend alive | Failure recorded; supervisor signals only verified PID/group/start identities, then bounded owned-container shutdown. Assert client/backend termination and container removal independently. Host subprocess exit is insufficient. Unverifiable termination => INCOMPLETE even if later disappearance is observed. | NOT RUN |
| Daemon disappears or changes identity between inspect/SQL/stop/removal | No guessed destructive fallback or remote/host connection. INCOMPLETE, retain sanitized run evidence. No cleanup success inferred from failed inspect or empty stderr. | NOT RUN |
| Stop deadline, surviving client, kill/rm error, auto-removal race, delayed/missing destroy event or unavailable resource evidence | Bounded ownership-checked stop then kill/rm only exact ID. Independent healthy-daemon inspect absence + separate ID-filtered absence + correlated destroy/runtime-release evidence required. Missing evidence/deadline violation => INCOMPLETE; no names/prune/host deletion. | NOT RUN |

## Stage 1.10 transaction and expected-error contract — NOT RUN

This is a non-executable specification. No SQL wrapper, derivative, supervisor,
fake or adapter is supplied. PostgreSQL transaction, lock, SQLSTATE and trigger
behavior below is expected from source and requires independent review and a
separately authorized runtime check. A bare SAVEPOINT plus ON_ERROR_STOP=1 is
insufficient: an uncaught error can exit psql before ROLLBACK TO is sent.

**T1: continuing statement probe.** Used inside the still-open S transaction
and inside an isolated F/U probe transaction. Before changing role/claims,
record the complete baseline and create a uniquely named outer savepoint. Set
the actual role and scalar/JSON claims transaction-locally, verify current_user
and auth.role, and verify the tested operation's exact identity. The future
reviewed test script must use an anonymous INVOKER PL/pgSQL block, with a nested
EXCEPTION subtransaction enclosing ONLY the single operation under test. Execute
the statement at the tested effective role, not through a SECURITY DEFINER test
helper. Dynamic statements must have reviewed literal identifiers/typed arguments;
the catch must cover execution/parse/ACL errors of that one statement too.
On error, GET STACKED DIAGNOSTICS captures RETURNED_SQLSTATE, message and constraint
identity into local variables after that subtransaction has rolled back its writes.
The handler accepts only the case's exact SQLSTATE AND diagnostic origin; all
other errors are re-raised. No catch encloses setup, assertion or cleanup.

Outside the nested catch, assert that exactly one operation was attempted, exactly
one expected error was captured (or zero for success/NULL cases), and the expected
return and state match. Unexpected success, wrong SQLSTATE/origin, missing marker
or wrong return causes an uncaught harness assertion error. Evidence includes case,
subcase, phase, role, exact entry identity, synthetic row IDs and observed SQLSTATE;
a generic P0001 is never enough to distinguish injected, source and harness errors.
Assertions and the evidence marker are outside the catch, so they cannot be
swallowed as expected errors. ON_ERROR_STOP stays 1 throughout; no client-side
toggle, reconnect or unreviewed psql-version-dependent error-variable recovery.
After an accepted expected error the outer transaction is healthy, permitting
RESET ROLE, owner snapshots and later S postconditions. Inspect state BEFORE
rolling back the outer savepoint; then ROLLBACK TO and RELEASE it to undo probe
setup, any successful writes, claims, role and local routing settings. Independently
compare the restored rows/catalog/claims/role to the pre-probe baseline in the
same S session. Sequence increments are not assumed transactional: capture their
values and treat any consumed value as a recorded disposable-lane effect; no
claim of byte-identical sequence state follows from rollback.

All S probes stay between the approved derivative's original BEGIN and final
ROLLBACK, on ONE connection. No probe wrapper may COMMIT or reconnect. After
final ROLLBACK an independent owner connection compares durable catalog, ACLs,
defaults, triggers and rows to the original pre-S baseline. Single-session
restoration establishes uncommitted S state; a second session cannot see it.
Unexpected error/assertion aborts further probes/postflight; client close plus
verified backend exit must roll back the outer S transaction. Missing final
rollback or independent comparison means INCOMPLETE, even if shutdown later works.

**T2: whole-file refusal/abort.** Used for uncaught migration/review/preflight
errors. Keep psql -X and ON_ERROR_STOP=1 with verbose error diagnostics; record
the exact failing statement marker, SQLSTATE, origin and nonzero client status.
Exit is expected only for the identified error, never a blanket nonzero-success
rule. Do not continue the aborted connection. Verify client/backend termination
or explicit rollback acknowledgement, then compare via a new owner connection
before lane destruction. Missing diagnostics/comparison => INCOMPLETE. M03's
before-COMMIT fault must be inside B05's file transaction; no outer wrapper can
undo an internal COMMIT. Disconnect/cancel injection must prove it occurred
before COMMIT; an ambiguous commit is a recovery finding, never a rollback PASS.

**T3: committed transitions and concurrent clients.** Each participant/step has
its own connection and explicit BEGIN/operation/COMMIT; capture durable results
from a separate owner connection after acknowledgement. Its expected-error
statement uses T1's nested subtransaction, but the participant then ROLLBACKs
its whole transaction after recording the expected failure. Any unexpected
error closes that client, cancels further work, terminates all tracked clients
and rolls back still-open transactions. Never treat a lock timeout (55P03),
statement timeout/cancel (57014) or deadlock (40P01) as an expected semantic
rejection. Reserved-generation 55P03 requires the B05 diagnostic origin.
Cross-session S requires separately approved exact COMMIT derivative bytes;
none exist here. Whole lane destruction replaces row-by-row deletion cleanup
for committed transitions, append-only audits and independently durable fake rows.

**C: unconditional independent cleanup.** Every M01–M21 entry inherits this
requirement, including negative, failed setup and failed assertion variants.
Run cleanup in finally; stop further statements/ledger writes on error. Record
each transaction's BEGIN, last acknowledged operation, COMMIT/ROLLBACK or close,
client/group/start identity and verified backend exit. Before destruction, where
access is healthy, capture independent durable rows/catalog and rollback evidence.
Destroy only the recorded newly created full ID after rechecking endpoint/engine,
token/name/purpose/image ownership. Use the existing contract's 20-second control
call and 60-second overall cleanup limits, stop 10 seconds, tracked TERM/KILL
verification 5 seconds each. Require healthy same-engine exact-ID inspect absence,
a separate successful exact-ID-filtered absence query, and correlated destroy/task
and tmpfs/scratch release evidence. Stop response, host CLI exit, failed inspect,
elapsed time or no visible name alone cannot establish cleanup. Missing evidence
means INCOMPLETE and no guessed destructive fallback. M21 mocks need an independent
observer/assertion, not a fabricated runtime release claim.

**A: assertion/completeness rule.** Every M case inherits this rule. A case
can be complete only if every declared subcase has its setup, operation, result,
poststate, restoration and C evidence. An assertion failure, skipped/blocked
subcase, source exposure, unexpected success/error, omitted marker or missing
independent cleanup leaves overall acceptance INCOMPLETE. Retain a separate
FAILED_CLEANED resource outcome if C passed; it is not a successful run. Future
process/report status must be nonzero on failed assertions, and must list unvisited
cases as NOT RUN, never infer success from zero psql exit or a caught error.
This package itself keeps ALL M01–M21 NOT RUN.

### Exhaustive expected PostgreSQL-error inventory for this matrix

NULL, false and JSON conflict/invalid_state/not_found are successful SQL
statements with negative semantic results; T1 asserts their exact return and
zero inappropriate writes, never substitutes an exception for them. SQLSTATE
P0001 for unqualified RAISE EXCEPTION is a proposed source/default interpretation,
not an engine observation. Symbolic insufficient_privilege/check_violation source
codes correspond to expected 42501/23514; ACL and FK denials require future engine
confirmation. Newly added errors need a new reviewed inventory row before use.

| Cases / expected error origin | Expected code and capture | Subsequent assertions and boundary | Status |
| --- | --- | --- | --- |
| M03 injected before B05 COMMIT | P0001 + unique injection marker; T2 | Compare migration-39 baseline/absent ledger40 only after aborted session exits; C | NOT RUN |
| M04 prepublication missing identity; B05 second application | 42883 for named uncommitted new identity; 42701 at first ADD COLUMN on reapply; T1 in independent client / T2 whole file | ACL catalog checks distinguish missing identity from denial; reapply baseline stays post-B05 | NOT RUN |
| M05 review stop / dependency stop | P0001 with each exact stop text; T2 | Independent original baseline comparison; never continue aborted file | NOT RUN |
| M06/M07 catalog/ledger preflight, postflight and injected tail failure | P0001 + exact named guard/injection; T2 for abort variants | Compare against already-tampered baseline, not untampered catalog; tail changes all roll back | NOT RUN |
| M08 effective table/column/sequence/utility denial; M09 client/private helper EXECUTE denial | 42501 + exact relation/routine/privilege denial; T1 | Zero row/audit changes; outer-savepoint restore then remaining S checks | NOT RUN |
| M09–M11 actor mismatch, revoked issuer, denied tenant admin or foreign grant scope | 42501 + corresponding actor/admin/scope source message; T1/T3 | Whole attempted grant/decision/finalization rolls back; legacy exposures are success findings, not errors | NOT RUN |
| M09/M10 unsupported role, inactive target/role/institution in grant; invalid reserve/finalize kind | 23514; seven-arg creator invalid role instead 22023; T1 | Assert exact first reachable guard and zero writes; do not collapse creator overloads | NOT RUN |
| M11 finalization reaches final DB decision clock after expiry | 23514 + 'Invitation expired during finalization'; T3 | Grant/audit writes rolled back; operation remains user_created; early expiry instead returns NULL | NOT RUN |
| M12 identity/terminal/expired rotation/premature expiry guard | 23514 + exact B05/legacy transition diagnostic; T1 | Unchanged invitation, operation, outbox, audit; keep enabled trigger evidence | NOT RUN |
| M12 reserved generation mutation / finalization without reservation / forged reservation | 55P03 reconciliation / 42501 finalization or reservation RPC required; T1 | One changed field per variant selects guard; unrelated lock timeout never accepted | NOT RUN |
| M12 parent/child scope constraint | 23514 from phase613 scope guards; T1 | Child/scope row unchanged; trigger definition unchanged | NOT RUN |
| M14 each actually reached audit INSERT fault | P0001 + table-specific fault marker; T1/T3 | Entire command state unchanged; fake provider state independently durable | NOT RUN |
| M15 guarded audit mutation; restrictive actor/institution deletion | 42501 append-only/ACL/TRUNCATE guard; 23503 identified FK; T1 | Populated rows, original event bytes/IDs unchanged; outer-savepoint restores allowed baseline mutations | NOT RUN |
| M15 reset TRUNCATE preflight extracted refusal | P0001 + 'Review public TRUNCATE triggers before resetting data'; T1 | Catalog predicate true already F/U; no reset SQL or destructive statement submitted | NOT RUN |
| M16/M17 advance invalid transition / recorded identity mismatch / missing Auth FK | 23514 exact advance diagnostic / 23503 users_auth_user_id_fkey; T1/T3 | Operation stays at prior committed stage, no partial public user/grant/audit | NOT RUN |
| M18 service claim denial | 42501; T1 | Wrong digest/kind/accepted mapping are NULL variants, not errors | NOT RUN |
| M19 student approver / prerequisites / grant scope; legacy approval denied | 42501 actor/scope or 23514 prerequisites; T1/T3 | Decision, grant and audit all unchanged; no org-admin success inferred | NOT RUN |
| M20 future function client/default EXECUTE denial | 42501 exact probe identity; T1 | Catalog ACL assertion plus real invoker denial; restore probe/default baseline | NOT RUN |
| M01 unexpected bootstrap/dependency/replay errors; M13 timeout/deadlock; M21 mocked transport/lifecycle errors | NOT expected PostgreSQL semantic errors | Fail closed, stop further statements; A/C. M07 hash gate has no SQLSTATE because no SQL is reached | NOT RUN |

## Stage 1.10 case-specific operation and state contracts — NOT RUN

The top matrix and existing audit/provider tables remain binding. The following
preconditions, operations and poststates refine them; a disagreement must block
acceptance pending review, not pick an easier oracle. Every case inherits T/C/A
above, so cleanup and incomplete-run semantics apply per subcase.

Notation fixes concrete fixture identities without repeating long UUIDs:
`U(n)`/`H(n)` = public/Auth 30000000-0000-0000-0000-<n padded to 12>;
`I(n)` = institution invitation 60000000; `P(n)` = platform invitation 61000000;
`R(n)` = request 50000000; `ST(1)` = student 51000000; `A/B/OA/OB` = tenant
20000000 suffix 1/2 and organization 10000000 suffix 1/2. D(n) is decimal n
left-padded to 64, matching I(n); P(n) uses D(100+n). Roles are resolved by unique
name (fixture ON CONFLICT may preserve a prior role UUID); never assume role IDs.
Every call is schema-qualified with explicit typed arguments and full signature.
Actual service_role SET ROLE plus scalar role='service_role', JSON role and
synthetic sub/email is the default; anon/authenticated tests set actual roles
and matching claims. Each variant starts from a fresh baseline or T1-restored
state; sequential variants must not borrow effects from an earlier variant.

Planned dynamic variant identifiers are RESERVED SPECIFICATION ONLY, not newly
loaded fixtures: `V(m,k,n)` = <90000000+m>-0000-0000-0000-<(1000*k+n) padded to
12>, for invitation in M=m, kind k=1 institution/2 platform/3 membership.
`Q(m,k,n)` uses <91000000+m> for operation; synthetic Auth `H*(m,k,n)` uses
<92000000+m>. Variant email `m<m>-k<k>-n<n>@example.invalid`; digest is numeric
(1000000*m+10000*k+n) left-padded to 64. All are collision-checked against fixtures,
including tenant+lower(email) invited uniqueness, token uniqueness and kind/invite
operation uniqueness. No deterministic raw credential is minted. When public
provisioning returns a server-generated ID, bind it as `U*` to H* and record it;
never invent a preselected RPC result. Variants require later exact setup-byte
review and success assertions before testing the operation. Default new-account
variant: invited admin/platform, issuer U(1), tenant A when applicable, no
reservation/user/grant/audit, expires server clock +7 days, created server clock
-1 day. Staff/faculty variants instead use U(12)/U(11) and R(6)/R(2), verified
canonical recipient and approved stored role; setup restores their original state.

Entry aliases (argument order is part of the contract):

| Alias | Exact public identity and typed ordered arguments |
| --- | --- |
| reserve | b05_reserve_invitation(text kind, uuid invitation, text digest, uuid Q, uuid existing_user, uuid existing_auth) |
| finalize | b05_finalize_invitation(text kind, uuid invitation, text digest, uuid Q, uuid target) |
| advance | b05_advance_invitation_operation(uuid Q, text expected_stage, text stage, uuid auth_id, uuid user_id, text first_name, text last_name) |
| lifecycle | b05_transition_invitation(text kind, uuid invitation, text status, uuid actor) |
| recover | b05_recover_accepted_invitation(text kind, uuid invitation, text digest) |
| assign4 / assign5 | phase81_assign_institution_role_audited(uuid actor, uuid target, uuid tenant, text role [, uuid actor_auth]) |
| create6 / create7 | phase717_create_invitation_with_outbox(uuid tenant, text email, text digest, timestamptz expiry, uuid issuer, text protected_marker [, text role]) |
| rotate | phase717_rotate_invitation_with_outbox(uuid invitation, text digest, timestamptz expiry, timestamptz expected_updated_at, text protected_marker, integer lock_seconds) |
| invite_approve7 | phase723_approve_membership_with_invitation(uuid request, uuid tenant, uuid actor, text reason, text digest, timestamptz expiry, text protected_marker) |
| immediate / reject | phase723_approve_membership_and_grant_role / b05_reject_membership(uuid request, uuid tenant, uuid actor, text reason) |
| decide | b05_decide_legacy_membership(uuid request, text approved_or_rejected, uuid actor, uuid actor_auth, text reason) |
| student | b05_approve_student(uuid student, uuid tenant, uuid actor, uuid actor_auth) |

Protected marker is repeat('SYNTHETIC_NOT_CIPHERTEXT_',5), lock_seconds=30,
first/last='Synthetic'/'Variant', reason='stage110 synthetic decision', unless
a variant explicitly changes one. These are data descriptions, not executable SQL.
For each positive RPC require full JSON/boolean result fields from its source,
not merely a truthy response. Stage 1.12 OB12 below explicitly lists terminal
outbox updates, creation and rotation before the zero-change rule is applied.
All other unlisted row-content/permission-grant/audit changes are forbidden;
zero row-count delta alone does not establish unchanged existing row contents.

### M01 — NOT RUN

Pre: F empty bare cluster; no application/Auth/ledger objects, no synthetic rows.
Operation: bootstrap then the exact 40 manifest filenames/bytes, each once as
postgres; no fixtures until replay completes. Expected all statements successful;
bootstrap requires server_version_num=170006, vector 0.8.0/btree_gist 1.7 in
extensions. Before each ledger entry assert that file's completion/commit. After:
ledger has exact 40 names/versions/statements and independent hashes; tables,
columns, overloads, triggers/owners/defaults equal source-derived inventory;
operations/lifecycle tables empty, no manufactured demo rows. B05 private tables
service SELECT only; new entry ACLs deny clients, private helpers deny service.
Capture grants and complete catalog independently of ledger. Historical source
seeds, if any, are reported as actual replay deltas, not fixture effects. Unexpected
dependency/bootstrap/replay error follows T2 failure, not an expected-error PASS.
C destroys lane; A requires all 40 files, ledger checks and prerequisite evidence.

### M02 — NOT RUN

Pre: U entries 1–39 committed; pre-fixtures loaded exactly once with recorded
DB anchor. Capture I(3/4/5), P(3/4), R(2/3/6), ST(1), U(1–12), all scoped roles,
permission grant 41000000 suffix 1 if seeded, historical audits 70000000/71000000
suffix 1 and outbox 63000000 suffix 1/2/6/7. Operation: unchanged B05 file alone,
then post-fixtures in a separate acknowledged transaction. Expected success;
before post-fixtures B05 adds nullable acceptance fields/decision_key, all NULL
on old rows, empty operations/lifecycle, no history backfill. Status, decision/time,
user/role/permission-grant/outbox/history bytes remain unchanged; R(2/6) approved
without grants/audits stays so. After post-fixtures verify snapshot 62000000/80000000
21–26 and their Auth/public/grant rows exactly as supplied, not reachable-RPC proof;
only specified rejection/repair audit inserts occur. Audit +column changes are
compared as old projections plus NULL, not claimed whole-row identical. Grants
as M01. T2 for setup/replay failures, C and A. Cutover policy remains B06/OD18.

### M03 — NOT RUN

Pre: U39 and pre-fixture baseline; version40 absent. Operation: separately
approved B05 negative derivative with one uniquely marked P0001 immediately
before its own COMMIT. Expected T2 exit at that injection, no later ledger write.
After aborted backend exit: every added column/table/function/index/trigger,
ACL/default and data projection absent/unchanged against U39; ledger40 absent.
Cancellation/disconnect before COMMIT is a separate subcase with no promised
P0001, requiring timing/termination evidence. ACL/grant/audit baseline must be
restored; version40 cannot be marked applied. C/A; derivative unavailable and
post-COMMIT response loss must be classified recovery, not this oracle.

### M04 — NOT RUN

Pre: F39, B05 applier's explicit transaction paused at reviewed barrier before
COMMIT; synthetic U(1/5) installed in a separate setup transaction if probes need
arguments. Operation: independent anon/authenticated sessions resolve and call
new b05_reserve_invitation identity with institution,I(1),D(1),Q(4,1,1),U(5),H(5).
Before commit catalog identity must be invisible; exact call expects 42883 (T1),
not 42501. After commit identity visible; same client calls expect ACL 42501,
service EXECUTE true and private helper EXECUTE false. No operation/grant/audit
row from either denied call; final catalog equals source. Other sessions must
not infer absence from a blocked/timeout query. Separate negative lane reapplies
B05 unchanged: expected first ADD COLUMN acceptance_id fails 42701, T2, durable
post-B05 baseline unchanged, no duplicate ledger write. Capture exact publication
barrier and final ACLs; C/A. No assumption of idempotence.

### M05 — NOT RUN

Pre: committed F/U post-B05 catalog/rows/ledger40. Operation: exact-byte validation
copy via T2; expected first stop P0001 text 'REVIEW-ONLY: NOT FOR EXECUTION;
independent exact-byte approval required'. Independent compare after close: no
catalog/ACL/default/data change and no successor ledger. Second stop only in
separately approved negative derivative removing first stop, expects P0001 text
'BLOCKED B01-B07: catalog/service/default/retention/security acceptance required
for executable successor'. Same rollback oracle; no body statements reached.
Each lane C/A; originals and copy remain byte-identical and stopped.

### M06 — NOT RUN

Pre: approved F/U baseline and exact reviewed S rollback derivative (absent).
Operation: original BEGIN, approved stop replacements, all original preconditions,
defaults/ACL/guard changes, T1 M08/M09/M12/M15/M20 probes before original postflight
and final ROLLBACK. Verify each probe restores S state including role/claims;
check postflight reached after an expected-error probe. Before rollback expected
client table/helper denials, retained service command EXECUTE, private helper
denial and admin no-TRUNCATE guard; no ledger added. After rollback independent
baseline catalog/data/ACL/default/trigger comparison, guard absent. Deliberate
unexpected-error variant must exit, skip later success markers and restore the
original baseline after verified rollback/close. C/A. S concurrency blocked without
another approved COMMIT derivative; do not run M13 from another connection to S.

### M07 — NOT RUN

Pre: N separate fresh lane per variant and approved negative derivative bypassing
only reviewed stops (absent). Capture untampered baseline, make exactly one owner
tamper in a committed setup, capture tampered baseline. Operation: successor
preflight/postflight with named failure stage. Hash variant is entirely separate:
mutate a private input-staging copy by one byte, keep approved digest unchanged;
future input gate must REFUSE BEFORE CREATE/SQL with mismatch path/expected/actual
hash, zero client/ledger/resource operations, no SQLSTATE. Manifest rehash is not
approval. SQL ledger cannot attest bytes; never tamper source files to test this.

Catalog variants and exact expected first guard (all P0001/T2):

| Single setup mutation | Failing source statement / diagnostic | Poststate |
| --- | --- | --- |
| Remove ledger40 / add synthetic 20990101000000 | $preflight$: Expected exact 40-version source chain (copy line 81) | Tampered ledger preserved, no containment changes |
| Required anon role made SUPERUSER / service BYPASSRLS false / client SET bridge to postgres | $preflight$: Missing/unexpected role / Unaccepted service RLS mode / Privileged inherited/settable role (65/69/74) | Setup remains; no new grants |
| Change a target table owner to service_role | $preflight$: Unreviewed table/type/owner/inheritance (87) | Tampered owner remains |
| Non-postgres service grantor on a target table/column (grantor=service_role, existing role only) | $preflight$: Unreviewed table/column grantee or grantor (96) | Tampered ACL remains |
| Add permissive client policy on target | $preflight$: Unreviewed client permissive policy (101) | Tampered policy remains |
| Add phase717_create_invitation_with_outbox(integer) owner postgres, no other changes | $preflight$: Unexpected overload (146) | Only setup overload remains |
| Change admin audit column type/layout, drop required default, drop NOT NULL, drop b05_decision_audit_key | $preflight$: Audit column type/layout / Audit default missing / Audit non-null contract; $b05_successor_layout$: B05 decision-key uniqueness contract mismatch (164/169/178/183/223) | Setup remains; earlier default revokes rolled back for layout/index failures |
| Rebind one listed trigger to another existing trigger routine | $preflight$: Guard changed (127) | Tampered binding remains |
| After all changes inject one forbidden client ACL before postflight | $postflight$: PUBLIC/client/unreviewed table/column grant or Effective table bridge (385/391) | Whole derivative including injected ACL rolled back |
| Tail injection just before original ROLLBACK, after postflight | Unique P0001 injection marker | Whole S changes rolled back |

The guard predicate is part of the oracle, not just the message. A changed default
expression with the default still present, or a different FK with equal counts,
is NOT guaranteed to fail the current SQL preflight; independent definition
comparison must reject it before body validation and record the predicate's
coverage limit. Do not report those variants as P0001 PASS without source support.
All data/audit/grant deltas zero except the approved tamper baseline; independent
owner comparison precedes C. A blocks acceptance if the wrong guard fails first.

### M08 — NOT RUN

Pre: populated F/U or uncommitted S; bind the exact successor target table list
and each live column/sequence/dependency from its source and captured catalog,
plus B05 operations/lifecycle. Operation per anon/authenticated and reachable
inherited/settable role: actual privilege query and T1 single SELECT, INSERT,
UPDATE, DELETE, TRUNCATE, REFERENCES/TRIGGER DDL on disposable objects referring
to the target. Use existing synthetic row, or collision-free V namespace and all
required FK fields; setup must itself succeed as owner. S expects 42501 and zero
changes for each targeted client command, no column bypass, no view/RPC bridge.
MAINTAIN is asserted by effective catalog privilege false within S, not by running
VACUUM in a transaction; utility behavior remains a separately approved lane.
F/U exposures are recorded from final ACLs, never assumed S denials. Service
B05 private SELECT succeeds with exact baseline rows; INSERT/UPDATE/DELETE/TRUNCATE
deny 42501, MAINTAIN false in F/U/S. S service admin_audit_log INSERT/SELECT allowed
with complete actor/tenant fields, UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER denied,
MAINTAIN false; successful INSERT rolled back. Other service grants use explicit
successor source allowlists rather than a blanket denial. Sequence probes require
USAGE/SELECT/UPDATE privilege contracts captured per sequence; no fabricated S
sequence revoke is assumed if source leaves it untouched. Unexpected bridge or
unresolved identity fails A; T1 restore, final S rollback if applicable, C.

### M09 — NOT RUN

Pre: F/U/S, roles and U(1/5/6/12), A/B, R(1/4/6). Capture every overload's arg
names/modes/defaults/result, owner/mode/path, ACL/grantor/options. Operation:
all service B05 entries have the typed calls and positive/negative variants in
M10–M19; client EXECUTE denial is tested for each with those same typed arguments.
Private functions b05_assert_platform_actor(uuid), b05_grant_institution_role
(uuid,uuid,uuid,text), b05_guard_invitation_acceptance(), b05_record_invitation_lifecycle
(text,uuid,uuid,boolean), b05_audit_invitation_transition(), and renamed
phase81_manage_faculty_section_assignment_original(uuid,uuid,uuid,uuid,boolean)
must have no service/client EXECUTE; direct attempts expected 42501 BEFORE trigger
function invocation/body validation. Proper nested positive calls demonstrate
owner use separately; no direct helper grant may be added to make them pass.
Close_unstarted(uuid,text) and expiry_candidates(integer) are service entries:
close I(2),'cancelled' => true with lifecycle event and OB12-T on outbox suffix 2;
expiry_candidates(200) includes
I(3) missing event, excludes P(3) (institution-only source), omits digest and
changes no rows. Invalid service claims expect 42501 on each entry's own check.

Specific legacy-versus-new probes (T1; each isolated):

| Identity / exact arguments | Before => expected after/result | Grants/audit consequence |
| --- | --- | --- |
| assign4(U(5),U(5),A,'admin') | No admin role => institution A/OA admin, true | Service permitted despite no platform actor; admin role.assignment +1. HARD BLOCKER |
| assign4(U(6),U(6),A,'staff') | Staff B/OB => staff A/OA, true | Same (user,role) scope overwritten, admin role.assignment +1. HARD BLOCKER |
| assign5(U(5),U(5),A,'admin',H(5)) | No role => 42501 Active platform administrator required, unchanged | Grant/audit delta0 |
| assign5(U(2),U(6),A,'staff',H(2)), R(4) made approved in setup | Staff B/OB => 42501 Existing role belongs to another scope, unchanged | No audit; approved setup remains until probe rollback |
| assign5(U(2),U(12),A,'staff',H(2)) | R(6) approved, no staff => true, staff A/OA | admin role.assignment +1; repeat false/delta0 |
| create6(A,'m9-create6@example.invalid',D(9001),DB now+7 days,U(1),marker) | No invitation/outbox => returned admin invitation ID, one pending outbox | Service EXECUTE, client42501; no membership/grant/audit change |
| create7(A,'m9-create7@example.invalid',D(9002),DB now+7 days,U(5),marker,'faculty') | No invite => faculty invitation/outbox despite unprivileged supplied issuer | Retained supplied-actor trust finding; no grant/audit; role='student' separately22023/delta0 |
| invite_approve7(V(9,3,1),A,U(5),reason,D(9003),DB now+7 days,marker) | Separate fresh pending staff request/recipient with no invitation => approved with supplied U(5), invitation/outbox | No guarded assignment, no decision audit; HARD BLOCKER, not immediate semantics |
| immediate(R(1),A,U(2),reason) | pending/no staff => approved, staff A/OA, role_granted/audit_persisted true | +1 role.assignment, +1 membership decision; M19 full retry oracle |

The invite_approve7 row's operation binds V(9,3,1), not R(1), in its independent
lane: synthetic public/Auth recipient H*(9,3,1), no role, pending staff A/OA request,
no invited email. Do not delete I(1) or disable FK/guards to stage this variant.
Return-generated invitation/outbox IDs must be recorded, not invented. Legacy
signature/behavior/grants remain untouched. M09 cannot pass containment acceptance
while these exposures persist. T1 state restore and independent C/A evidence.

### M10 — NOT RUN

Pre: I(1/6/7), P(1), U(1/2/3/4/5/8/11/12), R(2/6); no corresponding reservations.
Operation and exact result per single-change variant:

| Operation / setup | Expected result and row-level state |
| --- | --- |
| assign5(U(1),U(5),A,'admin',H(1)) | true; one admin A/OA grant and role.assignment audit; same repeat false/+0 |
| assign5(U(2),U(12),A,'staff',H(2)); faculty U(11)/R(2) variant | true; scoped stored role, one grant/audit each; no request decision overwrite |
| assign5 actor U(2) with H(3), or U(8)/H(8), or role claim missing/wrong | 42501 Verified actor identity mismatch or Service role required (first reachable check); zero changes |
| assign5(U(3),U(12),A,'staff',H(3)); U(4)/H(4) variant | 42501 active institution administrator required; org-admin desired compatibility remains unresolved |
| assign5 with U(12) inactive, role inactive, or tenant A suspended | 23514 grant Active target/configured role/institution when earlier admin checks pass; choose platform actor U(1) for these variants to isolate primitive guard |
| reserve institution,I(6),D(6),Q(10,1,1),U(12),H(12) | user_created,new_account=false, stored canonical IDs, invited row acceptance fields bound; no grant/audit |
| reserve same with wrong H(5), wrong recipient U(5), or stored R(6) email/role/status mismatch | NULL, no reservation/operation/grant/audit |
| reserve I(1) after revoking issuer U(1)'s platform role | 42501 Active platform administrator required; unchanged |
| reserve I(6) after revoking U(2)'s tenant-admin role | 42501 institution admin guard; unchanged |
| reserve institution with suspended tenant and otherwise valid issuer | NULL; distinguish it from assign's23514 |
| reserve platform,P(1),D(101),Q(10,2,1),U(5),H(5) | NULL even for existing matching recipient variant; no provider/grant |
| reserve/finalize kind='invalid', valid non-NULL args | 23514 Invalid invitation kind; no writes |

Malformed scalar/JSON claim syntax is unexpected setup failure, not an
authorization denial. Matching synthetic claims do not prove verified JWTs.
Finalization after recipient revoked/email changed => NULL and prior operation
unchanged; after issuer revoked =>42501; after R(6) loses approved state=>NULL.
Fresh valid finalizations have M14 audit deltas. Forged b05 GUCs are M12, not
identity proof. T1/T3 as appropriate, restore/destroy all variants, C/A.

### M11 — NOT RUN

Pre: both kinds V(11,k,n), invitation invited/no operation, configured issuer;
institution uses admin new account unless explicit existing recipient variant.
Operation reserve(kind,V,digest,Q,NULL,NULL): valid unexpired => reserved/new_account
true/IDs NULL; wrong D, NULL D/Q, missing ID, terminal row or already expired =>
NULL with zero row changes. Existing-user wrong recipient =>NULL. After correct
reserve, wrong digest=>NULL; correct digest with another caller Q=>original Q
reserved=true, no second operation; expired reserved=>same operation plus
reconciliation_required=true, not a new reservation.

Rotation order for institution uses rotate(V,new_digest,DB now+7 days,captured
updated_at,marker,30): before reserve returns sanitized invitation/outbox, updates
digest/expiry/resend_count(+1), cancels old pending outbox and inserts one pending
outbox; stale-digest reserve then NULL, current-digest reserve succeeds. Reserve
first =>rotate NULL and outbox unchanged. Platform has no corresponding rotate
RPC in this chain: use a single trusted service UPDATE token_hash/expires_at on
unreserved invited platform row, with guards enabled. Before reserve succeeds;
after reserve raises55P03, all unchanged. Expired unreserved direct rotation
raises23514 for both; RPC rotate on expired institution returns NULL.

**Decision-time expiry subcase**, both kinds, independent T3 lane: V(11,k,90),
Q(11,k,90), synthetic H*(11,k,90)/U* prepared via reserve/advance/fake to
user_created before expiry, no target role. Use a short-lived generation expiring
at an explicitly recorded SERVER clock +3 seconds at insertion, created_at -1
day; setup must reach user_created with at least 1.5 seconds remaining or discard
lane as INCOMPLETE. Blocker connection locks target U* FOR UPDATE first; finalizer
starts while unexpired, obtains invitation/operation locks, passes initial expiry
and reaches target lock. Independently prove that wait edge, then release blocker
after server clock exceeds expiry by at least 0.1 seconds and before elapsed lock
wait reaches 4 seconds (<5-second lock timeout; <120-second process deadline).
Failure to achieve this window/edge =>INCOMPLETE, not expiry PASS. A blocker-server
clock observation and lock-wait evidence are required; host sleeps alone are not
an oracle. Finalizer must specifically raise23514 'Invitation expired during
finalization', NOT early NULL, 55P03 or57014. After statement/transaction rollback:
invited, same Q/user_created/IDs; no target grant, accepted timestamp or audit
delta despite intermediate grant work. Auth/public previously committed rows
remain; no cleanup by account deletion. C/A. Timing mechanics/supervisor bytes
remain unimplemented and require review; source positive test has not run.

### M12 — NOT RUN

Pre: independent invited, reserved, accepted, cancelled, expired variants in
both kinds; populate valid accepted states through RPCs, not forged UPDATE.
Operation: actual service/owner single UPDATE with existing guards enabled.
Before/after operation in each error variant must match for invitation, operation,
outbox and audits. Identity change email/created_by/created_at =>23514 immutable;
institution tenant/role change =>23514 phase715 immutable. Terminal status reopen
or digest rotation=>23514 terminal. Accepted transition with OLD.acceptance_id
NULL=>42501 Finalization RPC required; do not combine other constraint-invalid
fields. New acceptance_id without matching routing setting=>42501 Reservation
RPC required. Reserved digest/expiry/Q/recipient ID change=>55P03 reconciliation.
Expired unreserved digest rotation=>23514; future invited status='expired'=>23514
has not expired. Direct invited->cancelled unreserved uses the complete C12
state/action/timestamp contract below; success has OB12-T plus lifecycle event
per M14. C12 distinguishes RPC retry, direct same-status UPDATE and historical
already-cancelled repair; these are not interchangeable timestamp oracles.

Forged GUC variant must explicitly record the trust limitation: matching
b05.acceptance_id on trusted direct service writes can pass the reservation
routing check; matching b05.recovery_id can permit reserved cancellation without
the RPC's provider-stage eligibility test. Synthetic service setting is NOT
authentication. Use reserved provider_started V(12,k,80) with forged recovery
setting and C12's complete direct cancellation: source guard permits it,
lifecycle and institution projection follow C12, operation remains provider_started.
Record this exposure, not a
denial PASS. Wrong GUC yields55P03. Client table ACL denial remains42501 regardless
of GUC. No new privilege, trigger disabling or source fix is authorized by this
probe; B01/B06 must decide direct-write authority.

Parent/child scope variants: UPDATE R(6).organization_id to OB while its
institution A remains OA, or insert a role scope pairing A/OB;
phase613 child/role guard expected23514 with exact constraint/trigger diagnostic
and no row delta. Record original full enabled bindings tgfoid/tgtype/tgenabled
and dependencies for B05 and phase715/phase613 guards. T1 restore/C/A; unsupported
alternate diagnostic or competing first guard requires review, not a widened catch.

### M13 — NOT RUN

Pre: separate fresh committed T3 lane per ordering, both clients' roles/claims
verified. Use V(13,k,n)/Q(13,k,n), real RPC transitions, no faults, missing target
grant. Capture explicit lock acquired/waiting edges and commits, with second
participant released before 5 seconds. Same-kind winning/losing participants
P1/P2 below are ordered by acknowledged row-lock ownership and commit, not host
launch time. Never accept deadlock/timeout as a winner. S concurrent lane absent.

| Pair, order and exact calls | P1 result; P2 result | Durable state / audit deltas |
| --- | --- | --- |
| reserve(V,D,Q1,NULL,NULL) then reserve(V,D,Q2,NULL,NULL), both kinds | P1 reserved Q1; P2 reserved=true with ORIGINAL Q1 | One reserved operation, IDs NULL, no grant/audit |
| finalize(V,D,Q,U*) then identical finalize, user_created beforehand | accepted=true; accepted=true,already_applied=true | Accepted same Q/U*/timestamp; one role; institution admin audits(+1 admin,+2 institution) or platform(+1 role), second+0 |
| Institution rotate then reserve old D; reverse | rotate sanitized JSON; reserve NULL. Reverse reserve succeeds,rotate NULL | Rotation winner: new digest/resend+1, old pending cancelled/new outbox+1,no Q. Reservation winner: old digest/Q,outbox unchanged,no audit |
| Platform trusted token UPDATE then reserve old D; reverse | UPDATE succeeds; reserve NULL. Reverse reserve succeeds,UPDATE55P03 | Same digest/Q ordering, no outbox; no audit |
| New-account reserve then lifecycle(cancelled,U(1)); reverse, both kinds | reserved; closed=true. Reverse closed=true; reserve NULL | Cancelled; reservation-first retains Q at reserved/IDs NULL, reverse no Q. lifecycle+1, institution admin projection+1; no grant |
| New-account reserve then lifecycle(expired,NULL); reverse | Reserve before expiry succeeds; lifecycle after DB expiry closed=true. Reverse lifecycle closed=true;reserve NULL | Expired same Q if first reserved, no Q if expiry first; lifecycle+1 issuer_for_expiry, institution admin projection+1 |
| Existing-account/user_created or provider_started reserve-state then lifecycle(cancelled/expired) | Reservation present; lifecycle NULL | Invitation/operation frozen, no event, no grant; source differs from unstarted NEW account |
| user_created finalize then lifecycle(cancelled/expired); reverse attempt while unexpired | accepted; lifecycle NULL. Reverse lifecycle NULL (ineligible stage); finalize accepted | Accepted grant/event exactly once; terminal command cannot close user_created operation |
| user_created expire-before-finalize | lifecycle NULL; finalize NULL on early-expiry check | Invited/user_created frozen, no grant/audit. Decision-clock23514 case is M11, distinct |
| immediate(R(1),A,U(2),reason) twice | first role_granted/audit_persisted,already_applied=false; second already_applied=true | Approved decision/time unchanged; staff grant +1,admin role.assignment+1,decision+1; second+0 |
| immediate then reject(R(1),A,U(2),reason); reverse | approve succeeds,reject NULL. Reverse reject succeeds,approve conflict=true | First decision retained; approve winner grant+1 and two admin events; reject winner no grant and one decision event |
| decide(R(1),'approved',U(2),H(2),reason) twice | decided=true,already_applied=false; decided=true,already_applied=true | One grant,+1 role.assignment,+1 membership.approved; stable decision/time; identical retry+0 |
| decide approval then changed reason/actor or rejected retry | First succeeds; each changed retry NULL | No state/event/permission-grant change from retries |
| invite_approve7 on V(13,3,90) twice / then reject | first already_applied=false with invitation/outbox; second already_applied=true / reject NULL | Request approved, one invitation/outbox, no grant/decision audit. Retained legacy gap |
| Two valid approved staff requests for SAME U(12) in A and B, invitation V(13,1,91/92), issuer U(2)/U(3), same role; finalize A then B / reverse | Winning tenant finalize accepted; other42501 Existing role belongs to another scope | One staff row in winner's scope; loser invited/user_created, operation IDs unchanged; one role.assignment, no scope overwrite, other audits0 |

For table rows1–12, n is that row's ordinal (1–12); use fresh lane per
ordering and k. Q1=Q(13,k,n), Q2=Q(13,k,n+100); the second reservation must return
Q1, not Q2. Membership V(13,3,90) and cross-tenant91/92 are the explicit exceptions.

For last row create distinct same-email invites in different tenants and matching
approved stored requests, verified recipient; stage both with existing-account
reserve before finalization, while no staff role exists. Capture both outcomes
and all surviving rows independently. New-account cancel/expiry after reserve
does NOT erase the reserved operation; later advance returns NULL for terminal
invitation. Product ordering preferences remain owner decisions. Stop all clients
on any unexpected outcome, T3 rollbacks/C/A; no unbounded waits.

### M14 — NOT RUN

Pre: fresh positive control fixture per command; V(14,k,n) user_created or
unreserved terminal-transition eligible; R(1/2/3/6), ST(1). Prove an unfaulted
control in a separate rollback lane reaches the intended INSERT and has the
existing audit-delta oracle. Install a fixture-only BEFORE INSERT fault trigger
as owner in setup, normal guards still enabled. Operation targets one table per
subcase with exact marker 'M14:<table>:<command>'; expected P0001/T1 or T3.

| Fault table | Actually reachable operations to test |
| --- | --- |
| admin_audit_log | assign5; institution admin/staff/faculty finalize; immediate; decide approved/rejected/retry repair; reject; student |
| platform_role_audit_log | platform finalize via phase712_assign_super_admin |
| platform_institution_audit_log | institution admin finalize; fresh admin cancel/expiry (not historical repair) |
| b05_invitation_lifecycle_audit | both-kind fresh cancel/expiry; missing-terminal-event repair |

Do NOT expect platform-role fault on institution staff, lifecycle fault on
finalization, or audit INSERT fault on invite_approve7: those bodies do not insert
that event. Invite_approve7 instead has a missing-decision-audit finding in M09.
Within each reachable fault operation: before/after request/student/invitation/
operation/user_roles/outbox/all audit rows identical to post-setup baseline; no
success return. Fault after role.assignment or first verified projection must
roll back earlier inserts too. Independently committed fake Auth/public rows
remain, create count unchanged; no SQL-provider rollback claim. Roll back setup/
outer savepoint and independently verify fault trigger absence/original bindings;
committed setup lanes destroyed with C. A fails if fault was never reached.

### M15 — NOT RUN

Pre: existing 70000000/71000000 history, lifecycle I(4) repair; add independently
reviewed populated platform_role/platform_institution synthetic rows with actor
U(1), target U(5), A, valid action/result per table checks. Capture their returned
IDs. Operation per service then owner: UPDATE one permitted payload field, DELETE
one row, TRUNCATE whole audit table, no CASCADE. Per-table F/U/S result is exactly
the earlier M15 table: expected42501 guarded mutations unchanged; unguarded
success yields changed/deleted/empty rows and is a recorded exposure, rolled
back before the next probe. S admin service and owner TRUNCATE42501, F/U admin
TRUNCATE success is a known baseline gap. T1 handles each expected denial.

Attribution operations lifecycle('institution',I(3),'expired',NULL) repairs one
missing event repaired=true/issuer_for_expiry/U(1), adds no projection; same retry
+0. I(4) existing event retry +0/original bytes; missing cancelled V(15,k,2)
terminal fixture with explicit U(2) repair=>repair_actor, absent actor=>unrecorded
initiator (separate variants). Fresh cancel/expiry variants have repaired=false
and earlier M14 deltas. Restrictive-FK isolated probes DELETE U(2) referenced
by admin audit and DELETE A with audit:23503 identified FK, zero deletions;
other restrictive references may fire first, so setup must isolate the named FK
or remain incomplete. Do not infer which constraint fired from23503 alone.

Maintenance subcase: inspect reset_supabase_data.sql lines38–44 and evaluate ONLY
its public/noninternal TRUNCATE-trigger predicate in F/U and S catalogs; assert
true from trg_b05_lifecycle_no_truncate already after B05, S adds admin guard.
A separately reviewed anonymous negative assertion of that same predicate/text
expects P0001 'Review public TRUNCATE triggers before resetting data' with T1.
Do not execute the reset file, create storage/provider shims to run it, or infer
that earlier Storage/matview checks passed. Rows/config stay unchanged. This
records B06 maintenance incompatibility before S, no replacement reset approved.
Rollback each allowed mutation/setup; independent baseline comparison, C/A.

### M16 — NOT RUN

Pre: V(16,k,n) for BOTH kinds, new-account/admin, no Auth/public/operation/grant;
approved offline fake and loss injector absent. Operations in separate T3 commits:
reserve(kind,V,D,Q,NULL,NULL); advance(Q,'reserved','provider_started',NULL,NULL,
'Synthetic','Variant'); one fake create H* (owner-only auth.users insert,
unconfirmed); advance(Q,'provider_started','provider_created',H*,NULL,...);
advance(Q,'provider_created','user_created',H*,NULL,...), recording returned U*;
finalize(kind,V,D,Q,U*); fake confirm same H*; advance(Q,'accepted','confirmed',
H*,U*,...). Each expected positive step returns its exact stored stage/IDs or
accepted JSON. Record all rows and fake-call counts before and after EACH step.

Inject separately immediately before COMMIT and immediately after independently
observed COMMIT with response withheld for each SQL step. Before commit rollback
leaves prior stage/IDs; after commit resolver reserve(kind,V,D,Q2,NULL,NULL)
returns ORIGINAL Q/current stage, never creates a new operation. Provider-start
commit response loss freezes even with fake count0; do not infer permission to
create from absent response. Provider-ID and provisioning loss resumes by recorded
stage; accepted lost response finalize returns already_applied, audits+0. Missing
Auth row when provisioning reaches public.users FK expects23503 (record exact
users_auth_user_id_fkey); mismatched existing public email/status expects23514
Recorded identity mismatch; neither yields partial provisioning or grants.
Auth account ID recorded at provider_created is not itself Auth-row validation.
M17 covers independent fake unknown outcomes. T3/C/A; post-fixture snapshots
alone never satisfy a step or proof of reachability.

### M17 — NOT RUN

Pre: both V(17,k,n)/Q(17,k,n) at committed provider_started from real RPCs,
IDs NULL, no Auth/public/grant; reviewed durable fake with exact H* correlation.
Operation per independent variant: fake create once then lose response; fake
create returns missing ID; record-ID advance commits then lose SQL response;
record-ID advance before-COMMIT failure. First two =>one unconfirmed Auth H*,
fake durable evidence binding kind/V/D/email, operation provider_started/IDs
NULL, no public/grant/audit; replay may inspect but create count stays1 and
must freeze. CAS response lost before fake call =>count0 and still freeze.
Recorded-ID committed=>provider_created/same H*, resolver sees it, count1.
Before commit=>provider_started, retained Auth H*, count1; only approved correlated
fake evidence can authorize same-ID advance, never guess ID or blind second create.

SQL variants advance(Q,'provider_started','reserved',NULL,NULL,...) and clearing
recorded ID through invalid transition =>23514 Invalid operation transition
when expected_stage matches; wrong CAS expected stage=>NULL with unchanged
operation. lifecycle(kind,V,'cancelled'/ 'expired',U(1)) while provider_started
=>NULL, no terminal event; close_unstarted institution=>false. Direct service
private-state UPDATE=>42501. Missing/mismatched Auth/public variants follow M16
23503/23514, not a blanket error. No compensation/delete/password reset.
Independent fake transcript and owner SQL snapshots must agree; conflict remains
INCOMPLETE. T1/T3/C/A, no GoTrue guarantee or real provider observation.

### M18 — NOT RUN

Pre: V(18,k,n)/Q(18,k,n), H*/U* at accepted through real M16-style transitions,
canonical active matching email, new_account=true, correct grant/audit IDs;
separate confirmed variant and institution existing-account variant using U(5).
Operation recover(kind,V,D): accepted=>exact Q/stage/recorded Auth/public IDs;
confirmation-only fake retry confirms SAME H*, no create/password work, then
advance accepted->confirmed and reserve/recover retries return confirmed current
operation with no provider calls. Wrong digest/NULL digest, kind='invalid', absent
ID, status not accepted, existing-account new_account=false, mismatched operation
kind/invitation/user, missing recorded Auth ID, inactive U*, changed email or
changed public Auth mapping=>NULL, zero SQL/fake writes. Setup of private mismatch
variants is owner-only isolated snapshot tampering and never transition proof.
Missing service role claims=>42501. Revoking ROLE alone while canonical accepted
user stays active is a separate source limitation: recover does not recheck
membership grant or issuer; same correct accepted operation can still return.
Likewise accepted expiry alone is not checked here. Record B06/OD retention/
revocation policy open, do not invent denial. Accepted confirmation failure/lost
response leaves operation accepted and may leave Auth confirmed independently;
retry is confirmation only. All grants/audits/operation identity preserved;
T1/T3/C/A, no credentials emitted.

### M19 — NOT RUN

Pre: R(1/2/3/4/6), ST(1), U(2/4/5/6/7/9/11/12), actual permission grants captured.
Operations immediate/reject/decide/student use exact aliases above. Immediate
R(1) => approved byU(2)/reason, grant staff A/OA, two admin events as M14;
repeat=>already_applied=true, original decision/time, no additional events.
R(2/6) approved without grant=>immediate invalid_state=true/zero writes; separate
decide identical stored actor/reason repairs missing grant plus one decision
event and role.assignment. Existing preapproved reason for this retry is
'synthetic legacy decision', actorU(2)/H(2), not the default new reason.
Reject R(1)=>rejected/one correlated event/no grant; repeated reject repairs absent
event once, preserves decision/time. R(3) existing rejected/audit/grant=>retry+0
and preserves U(7) role AND permission grant bytes. Decide identical retry succeeds,
changed actor/reason or opposite terminal status=>NULL. Source immediate/reject
do NOT enforce changed-actor/reason conflict on already-decided same-status
retries; original decision remains and original actor is used for repair. Record
this distinction, don't apply decide's stricter oracle to those routines.

Decide approved R(4) with adminU(2)/H(2)=>42501 foreign staff scope, request stays
pending, all grant/audit bytes unchanged. Org-adminU(4)/H(4) approval R(1)=>42501
tenant admin guard, full rollback, desired service compatibility unresolved.
Student(ST(1),A,U(2),H(2))=>approval approved, student A/OA grant if absent,
exactly one student:<ST> event, no staff/faculty invitation added. Wrong actor/auth
=>42501; inactive student recipient/missing role=>23514; existing student grant
B/OB=>42501 scope conflict. Repeat returns student/grant/audit true, original event
bytes/+0. Injected admin INSERT fault uses M14 P0001/full rollback. The T19
contract below separates tenant-boundary 42501 from authorized lookup-miss
not_found/NULL; each binds its request, supplied tenant and actor. Invalid requested role=>immediate
invalid_role; invalid_state fields yield exact JSON with no grants. No provider
confirmation/HTTP readiness claim. T1/T3/C/A.

### M20 — NOT RUN

Pre: uncommitted S after default changes, owner/default ACL baseline captured;
probe schema and identity names vacant. Operation owner postgres creates
transaction-local public.b05_stage110_probe_public() and separate-schema
b05_stage110_probe_schema.b05_stage110_probe_other() invoker functions returning
integer1 (future setup bytes separately reviewed). Assert actual creator postgres.
Global PUBLIC EXECUTE removed in both schemas; public anon/auth direct defaults
removed; public service default remains and actual service call returns1, while
anon/auth public call42501. Grant only USAGE to test roles on probe schema in
outer-savepoint setup to isolate function denial; cross-schema client EXECUTE
still denied42501. Other-schema service EXECUTE follows captured per-schema
baseline, not assumed public service default. Another-creator behavior remains
an explicit B03 question; if authorized, dedicated NOLOGIN/NOBYPASSRLS creator
and known baseline must be separately reviewed, no inherited postgres assumption.
Vector dependency checks resolve extensions.vector(1536)/cosine operator/HNSW
class and run a transaction-local populated probe only in later authorized S;
retained trigger/helper nested consumers use positive M09/M12 paths and existing
approved academic fixtures, whose exact bytes are still unavailable for wider
attendance/test chains. That wider scope is BLOCKED, not silently passed.
No extension reinstall or source ACL/body modification. No application row/audit
delta from default probes; T1 rollback removes functions/schema/grants and restores
S catalog; final ROLLBACK independent pre-S comparison. C/A; cross-schema creator
and future service-default impact remains B02/B03/OD17.

### M21 — NOT RUN

Pre: a future independently reviewed adapter/startup/supervisor with pinned bytes
and separate approval (all absent). Synthetic mocks use token
0123456789abcdef0123456789abcdef and full ID D(2101), labels/name from contract;
these are mock identifiers ONLY, never accepted as real fresh-run ownership.
Operation inject each failure in the earlier M21 table at gate/create/start/
bootstrap/replay/ledger/copy/SQL/termination/removal boundaries. Mock independent
observer asserts exact command log/zero forbidden calls; compare mocked resource
registry before/after. Gate refusals: no create/start/SQL/ledger. Failures after
proven create: no further replay/ledger and only that full ID eligible for
ownership-rechecked bounded cleanup. No SQLSTATE assigned to transport/control
failure. SQL failure mocks preserve failed-file absent ledger; post-COMMIT ledger
failure destroys lane. Resource absence and three independent evidence streams
must all be present for mocked cleanup success; missing/contradictory ownership,
daemon change, backend survival or evidence=>INCOMPLETE/nonzero status. Also
inject assertion mismatch AFTER expected SQL error capture: report INCOMPLETE,
no later success marker, finally cleanup still attempted only with ownership proof.
Required grants/denials are zero database reachability on preflight refusal and
no expansion of existing guard purpose allowlist. No synthetic mock grants may
be counted as effective PostgreSQL ACL evidence. No real engine resource-release
claim from mocks. C/A independently required for any later engine lane. Current
preparation nine offline unit tests do not satisfy M21.

### Source evidence anchors for Stage 1.10

These refer to preserved raw-byte files, with line numbers at this stage; no
deployed catalog or engine semantics are claimed. Full identities/bodies in
these files take precedence over shorthand above and must be reviewed again if
bytes change. A first error arising from an earlier predicate must be explained
and the variant restaged, not accepted under a generic code.

- B05 migration `20261017000000_b05_invitation_acceptance_security.sql`: grant
  55–102; assign5 105–149; guard152–203; reserve210–320; finalize322–424;
  entry/private ACLs426–435; rotate437–515; immediate523–623; advance627–682;
  student690–737; reject741–770; decide775–824; lifecycle827–934;
  close-unstarted939–947; recovery950–975; institution-only expiry candidates979–993;
  transaction9/995.
- Phase8.1 `20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql`:
  assert institution admin132–165; four-arg assignment389–481; service grant494;
  phase81_prevent_audit_mutation definition in that same file.
- Onboarding `20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql`:
  create7 at20–59, unsupported role22023; invite_approve7 at103–168, no guarded
  actor binding or decision INSERT. Immediate B05 replacement is a different identity.
- Successor validation copy: BEGIN39, stops42/45, preflight52–201, B05 layout207–225,
  new no-TRUNCATE helper344–352, postflight354–471, final ROLLBACK475; no byte hash
  ledger column. Original candidate's11-column/39-version expectation preserved.
- Pre/post fixture files define concrete baseline rows; bootstrap defines synthetic
  role/claims/Auth/ledger only. Legacy institution transition guard Phase7.15,
  scope guards Phase6.13, private assignment rename faculty-validity migration,
  public.users Auth FK reconstructed baseline, and maintenance reset predicate38–44
  must be compared to their complete pinned source bodies before future probe review.

## Stage 1.12 OB12 outbox state contract — NOT RUN

This section resolves only the three Stage 1.10 independent-review findings.
It refines the existing cases without adding an executable fixture, wrapper,
runner, worker or provider call. Every operation still inherits T1/T2/T3/C/A.
OB12, C12 and T19 are mandatory source-derived expectations, NOT observations.

**OB12-S: finite source fields and baseline.** Capture full rows of
public.email_outbox, public.email_delivery_attempts and public.email_delivery_events
before/after, including unrelated rows and existing provider-correlation fields.
Compare by primary key, not counts alone. The outbox observation columns are:

`id, message_type, aggregate_type, aggregate_id, protected_token, status, attempt_count, available_at, locked_at, sent_at, failed_at, delivery_updated_at, provider_name, provider_message_id, last_error_category, created_at, updated_at, delivery_sequence`.

Source: [worker schema:7–51](../../../supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql#L7)
and [delivery_sequence:6–10](../../../supabase/migrations/20261002010000_phase_7_18_mailgun_webhook_reconciliation.sql#L6).
There is **no outbox version column**. delivery_sequence is a generated identity
for delivery ordering, not an update version or invitation generation. Existing
id/delivery_sequence and attempt_count remain unchanged on terminal updates;
capture new returned IDs/sequences on inserts, without predicting contiguous
identity values or sequence rollback. Invitation generation is its stored
token_hash/expires_at; rotation additionally changes invitation resend_count.
No delivery-attempt/event rows or provider calls are produced by terminalization.

Base pending row: bind its actual id and aggregate_id to the institution
invitation; message_type='admin_invitation', aggregate_type='platform_admin_invitation',
status='pending', attempt_count=0, locked_at/sent_at/failed_at/delivery_updated_at/
provider_name/provider_message_id/last_error_category NULL, protected_token equal
the synthetic marker, available_at/created_at/updated_at equal captured fixture
anchor. Record generated delivery_sequence. For fixture I(1/2/6/7), IDs are
63000000 suffix 1/2/6/7 exactly
([pre-fixture:101–111](../../../scripts/validation/b05_containment/fixtures_pre_b05.sql#L101)).
Dynamic institution variants in M11–M16 must specify one owner-staged pending
row O(m,n) = <93000000+m>-0000-0000-0000-<n padded to 12>, aggregate_id=V(m,1,n),
with the same valid fields and recorded sequence, before the operation baseline.
These are collision-checked, future-reviewed setup descriptions only. Additional
control rows use distinct n and are bound explicitly to the tested aggregate
or an unrelated institution invite. No email_outbox row may refer to a platform
invitation: its aggregate_id FK references platform_admin_invitations only.

**OB12-T: required terminal change.** Before: institution invitation status
invited with P matching pending outbox IDs, including the base pending row.
After a successful invited->accepted/cancelled/expired transition: every one of
those same P IDs has status='cancelled', protected_token=NULL, locked_at=NULL,
last_error_category='INVITATION_TERMINAL', updated_at equal the operation
transaction's observed now() (Tsql). All other outbox columns, including
attempt_count, available_at, sent_at, failed_at, delivery_updated_at, provider
correlation, created_at, aggregate_id and delivery_sequence, are unchanged.
Total row count, IDs and attempt/event histories are unchanged. P=0 is a separate
no-pending-row variant; it cannot satisfy a positive pending-row assertion.
Source: [terminal trigger:112–128](../../../supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql#L112).

**OB12-N: forbidden change.** Non-pending rows of the same aggregate and all
unrelated rows remain identical in every field under OB12-T. Include separately
reviewed processing control (non-NULL locked_at, synthetic protected_token,
attempt_count=1 and a matching existing attempt), and cancelled/sent controls
(NULL protected_token/locked_at), with distinct IDs/sequences and valid checks.
The trigger's pending predicate leaves a processing row and its attempt intact;
do not assert processing-token clearance or delivery cancellation. This is a
source limitation within open B06, not an approved worker/provider guarantee.
No worker, webhook or lease-recovery routine is invoked in these terminal probes.
Denied/NULL/invalid-state operations, reserve/advance/recover and SQL rollback
leave the appropriate pre-operation outbox baseline unchanged unless OB12-C/R
below explicitly lists another mutation.

**OB12-I: idempotent retry.** Already-accepted finalize, same-terminal lifecycle
RPC, close retry and historical repair do not perform an invited->terminal
transition, so every outbox/attempt/event row remains identical to its immediate
retry baseline. Deliberately owner-staged pending rows on historical terminal
invites also stay pending: repair is not a cleanup sweep. No fabricated worker
call may make them disappear. Lifecycle repair may add its one missing audit
event under the existing audit oracle, without changing outbox. Accepted resolver,
recovery and confirmed-stage advance preserve the terminal outbox snapshot.
Source: [accepted early return:353–358](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L353),
[lifecycle repeat:907–930](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L907).
All platform variants preserve the entire institution outbox independently of
their platform grant/lifecycle result; there is no platform outbox implementation
or invented platform terminal-email trigger in this chain.

**OB12-C: creation.** For create6/create7/invite_approve7 positive controls,
require no pre-existing invited row with the same tenant/lower(email), so their
housekeeping UPDATE touches nothing. Returned email_outbox_id identifies exactly
one new pending row whose aggregate_id is the returned institution invitation ID;
assert marker, attempt_count=0, defaults and NULL fields from OB12-S. available_at,
created_at and updated_at equal Tsql; record generated delivery_sequence. Prior
outbox/attempt/event rows are unchanged. Identical invite_approve7 retry has no
new invitation or outbox row; assert original IDs and OB12-I. Standalone create
is not promised idempotent. If a separately reviewed same-email expired setup
is ever used, its housekeeping terminalization needs OB12-T and existing B05
eligibility checks; do not borrow the no-housekeeping baseline.
Source: [create6:152–177](../../../supabase/migrations/20261002000000_phase_7_17_email_outbox_worker.sql#L152),
[create7:37–60](../../../supabase/migrations/20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql#L37),
[legacy retry:103–168](../../../supabase/migrations/20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql#L103).

**OB12-R: existing pending-only rotation.** Stage matching pending row(s), no
processing row or lease recovery, invited/unreserved/unexpired invitation and
captured expected_updated_at. Successful rotate cancels all old matching pending
IDs with the OB12-T field changes except last_error_category='INVITATION_SUPERSEDED';
inserts exactly one new pending row with returned email_outbox_id, same aggregate,
marker/attempt_count=0/defaults/Tsql and independently recorded delivery_sequence.
Existing sequence/attempt fields are unchanged; new sequence is distinct, not an
incremented version of the old row. Invitation digest/expiry/resend_count(+1),
email_delivery_status='pending', email_delivery_at=NULL and updated_at=Tsql are
asserted separately. Reserve-first, stale expected_updated_at or expired RPC
refusal returns NULL before rotation mutations; OB12-N. Reusing the OLD expected
timestamp after a successful rotation is a NULL/no-change retry only when the
observed timestamp actually differs; otherwise do not infer a conflict from
time passage. No general rotation idempotence is asserted.
Source: [B05 rotate:452–514](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L452).

**OB12 affected-case register.** Each row inherits full OB12-S snapshots and
compares after the operation, before T1 restoration, then after rollback/commit.
On any fault/denial, all terminal/rotation/creation mutations roll back with the
command. Row IDs/contents restore; consumed identity sequence values need not.

| Case | Operation-specific outbox oracle | Status |
| --- | --- | --- |
| OB12/M01 | Empty-chain replay: no fixture rows; outbox/attempt/event catalog and source replay baseline recorded, no invented queue. | NOT RUN |
| OB12/M02 | Pre-fixtures insert suffix 1/2/6/7 pending rows as OB12-S. B05 and post-fixtures preserve those rows/IDs/attempts/sequences exactly. | NOT RUN |
| OB12/M03 | Before-COMMIT B05 failure restores all pre-B05 outbox/attempt/event rows. | NOT RUN |
| OB12/M04 | Denied pre/post-publication calls and failed reapply cannot mutate outbox. | NOT RUN |
| OB12/M05 | Both stopped-copy refusals preserve all outbox rows/history. | NOT RUN |
| OB12/M06 | Each contained probe follows its OB12 mode; T1 restoration and final S rollback restore original outbox contents. | NOT RUN |
| OB12/M07 | Hash refusal reaches no SQL; catalog/tail refusal restores already-tampered outbox baseline without new queue work. | NOT RUN |
| OB12/M08 | ACL/bridge denials leave outbox/history unchanged; no worker positive control is implied. | NOT RUN |
| OB12/M09 | close I(2) requires OB12-T on suffix 2; client/claim refusals OB12-N; expiry_candidates read only; creators/legacy invitation approve OB12-C, identical legacy retry OB12-I. | NOT RUN |
| OB12/M10 | reserve and identity/issuer/scope failures OB12-N; valid institution finalize OB12-T including suffix 1/6/7 when used, accepted retry OB12-I; platform has no outbox changes. | NOT RUN |
| OB12/M11 | Rotation OB12-R, reserve/refusals OB12-N. Decision-clock 23514 restores pending row and marker, no terminal cancellation; successful finalization control OB12-T. | NOT RUN |
| OB12/M12 | Complete C12 direct cancellation OB12-T; forged recovery cancellation also OB12-T if eligible checks pass. Guard/CHECK denials OB12-N; same-terminal retries OB12-I. | NOT RUN |
| OB12/M13 | Institution acceptance/cancel/expiry winner OB12-T; retries/losers OB12-I/N; rotation winner OB12-R; cross-tenant winning invite cancels its own pending queue only, scope-denied loser preserves its queue; legacy create/retry OB12-C/I. | NOT RUN |
| OB12/M14 | Unfaulted controls OB12-T/C/R as applicable; reached audit INSERT fault restores all pending/attempt/event rows and marker even if a trigger updated them before the fault. | NOT RUN |
| OB12/M15 | Fresh cancel/expiry OB12-T; historical repair/repeat OB12-I including any intentionally staged pending historical row; audit mutation/reset-predicate probes OB12-N. | NOT RUN |
| OB12/M16 | Before finalization pending row stays pending across reservation/provider/provision steps; finalize commit OB12-T, before-COMMIT fault restores pending, after-COMMIT lost response retains cancelled row; resolver/retry/confirm OB12-I. | NOT RUN |
| OB12/M17 | Provider uncertainty, invalid advance/close and failed provisioning preserve staged pending queue/history (OB12-N); no delivery work from provider fake. | NOT RUN |
| OB12/M18 | Accepted/confirmed baseline obtained with OB12-T; recovery/confirmation retries, including rejected recovery, preserve that exact terminal outbox (OB12-I/N). | NOT RUN |
| OB12/M19 | Immediate/reject/decide/student and T19 denied/lookup-miss variants leave invitation/outbox/attempt/event rows unchanged; these identities do not create invitation email. | NOT RUN |
| OB12/M20 | Default/vector/consumer probes preserve queue/history; T1 and final S restoration compare full rows. | NOT RUN |
| OB12/M21 | Mock gate denial reaches no database. Failure/cleanup assertions do not invent PostgreSQL outbox evidence; future SQL failures inherit the affected case's rollback baseline. | NOT RUN |

## Stage 1.12 C12 complete cancellation setup — NOT RUN

**C12 initial state.** For each kind k, collision-checked V(12,k,70) has email
m12-k<k>-n70@example.invalid, digest from V notation, issuer U(1), created_at=
fixture_anchor-1 day, expires_at=fixture_anchor+7 days, status='invited'; accepted_at,
accepted_user_id,cancelled_at and all three acceptance fields NULL. Institution:
tenant A, role_name='admin', updated_at=fixture_anchor, email_verified_at=NULL,
email_delivery_status='pending', email_delivery_attempts=0, resend_count=0,
email_delivery_at/last_sent_at NULL.
Platform has no institution/role/delivery/updated_at columns: do not invent them.
No operation, grant, lifecycle or projection event exists for this invite. For
institution use OB12-S pending row O(12,70), plus valid non-pending/unrelated
controls; for platform record unchanged institution queues, not a platform row.
Source: [institution schema:26–91](../../../supabase/migrations/20261001020000_phase_7_14_super_admin_university_admin_lifecycle.sql#L26),
[delivery additions:40–94](../../../supabase/migrations/20261001030000_phase_7_15_invitation_delivery_email_verification.sql#L40),
[platform schema:8–29](../../../supabase/migrations/20261008000000_phase_9_super_admin_invitations.sql#L8),
[B05 additions:11–18](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L11).

**C12 direct action.** Actual service_role with scalar/JSON role='service_role',
sub=H(1), email=platform@example.invalid; verify role/claims and baseline. Use
transaction-local b05.acceptance_id/b05.recovery_id/b05.lifecycle_actor empty
(or absent), with all normal guards enabled. Set ONLY status='cancelled' and
cancelled_at=Tcancel, where Tcancel is the validated fixture_anchor supplied
as explicit timestamptz. Preserve accepted_at/accepted_user_id NULL and every
other invitation column. This is a textual UPDATE contract, not submitted SQL.
The deterministic value is supported by existing fixture_anchor plumbing;
neither the database clock nor clock_timestamp() is mocked. Expected one changed
invite, final cancelled_at exactly Tcancel, status cancelled, identity/digest/
expiry/acceptance/delivery fields unchanged (institution updated_at unchanged).
OB12-T updates institution pending outbox at Tsql, which is the observed
transaction now(), not Tcancel. Lifecycle +1 repaired=false, attribution=
unrecorded_initiator, actor_user_id=NULL; institution admin projection +1 with
issuer fallback U(1), platform projection +0. No operation/grant/attempt/event
changes. Source: [guard:152–203](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L152),
[lifecycle trigger/record:838–889](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L838).

**C12 distinct negative/exposure variants.** Institution status-only cancellation
with cancelled_at still NULL expects 23514 identifying
platform_admin_invitations_terminal_state_check; no outbox/audit/invite change.
The platform schema has no equivalent timestamp CHECK; do not require that
denial there. For existing V(12,k,80) provider_started exposure, build the stored
Q via real reserve/advance transitions, then use the SAME complete direct action
with b05.recovery_id equal its recorded Q and other routing settings empty.
Acceptance fields/Q remain as recorded, operation stays provider_started;
cancelled_at=Tcancel, OB12-T and lifecycle/projection changes as above. Wrong
recovery setting expects55P03 'Invitation acceptance requires reconciliation',
all rows unchanged. This documents the existing trusted-service boundary, not
its acceptance or a repaired authorization check.

**C12 retries/already-cancelled.** After successful direct cancellation, an
identical direct UPDATE retaining Tcancel may run and preserves timestamp and
all invitation fields. AFTER UPDATE OF status may try event repair; an existing
event remains byte-identical/+0 and projection +0, OB12-I. For a separately
staged historical cancelled invite with no lifecycle event, preserve its original
cancelled_at and identity; lifecycle(kind,V,'cancelled',NULL) returns closed=true,
already_applied=true, adds exactly one repaired=true/unrecorded_initiator event,
no historical projection and OB12-I. Retry adds zero events. Fresh lifecycle RPC
cancellation instead assigns clock_timestamp() itself: record server bounds
immediately before/after and require cancelled_at within them; its later repeat
preserves the exact returned timestamp. It is not expected to equal fixture_anchor.
The guard does not prohibit changing cancelled_at alone on a cancelled row;
therefore only identical direct retries are asserted idempotent, not arbitrary
direct timestamp overwrites. Source: [guard terminal field list:163–172](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L163),
[RPC clock/repeat:907–933](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L907).
T1 captures restored state after each variant; C/A remain mandatory.

## Stage 1.12 T19 wrong-tenant actor setup — NOT RUN

**T19 boundary actor/resource.** Actor U(2)/H(2), admin-a@example.invalid, is an
active confirmed synthetic public/Auth identity with exactly the active 'admin'
role scoped institution A/OA; no role in B, no organization/platform role and
no additional permission grants. Both A and B are active. Create a pending
membership target RB=R(4), owner-restaged from A/OA to B/OB before the baseline,
for active confirmed U(6)/H(6), email
existing-b@example.invalid, requested_role='staff', all decision fields NULL,
created_at=fixture_anchor-2 days, updated_at=fixture_anchor-1 day. U(6)'s existing
staff B/OB grant is a recorded unchanged baseline, not a newly authorized grant.
Preserve R(4)'s existing ID rather than inserting a duplicate pending
(user_id,requested_role) pair; only institution_id/organization_id are restaged
to B/OB together under the enabled scope guard. No invite or outbox is added.
Fixture actor grants come from
[pre-fixture:20–45](../../../scripts/validation/b05_containment/fixtures_pre_b05.sql#L20).
RB's tenant restaging is a future-reviewed owner setup description, not a
changed fixture file. Source scope/unique predicates:
[membership schema/index:582–693](../../../supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql#L582),
[child guard:709–754](../../../supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql#L709).

Actual SQL role service_role, scalar role and JSON role='service_role',
sub=H(2), email=admin-a@example.invalid. Bind supplied actor U(2) to H(2) in
the synthetic claim baseline, verify current_user/auth.role and identities.
Both routines have service EXECUTE: refusal must arise inside the administrator
guard, not from missing claims/EXECUTE/RLS, malformed arguments or absent target.
The guard uses the supplied actor's active admin scope; immediate/reject do not
receive an actor_auth argument or validate the claim subject as human identity.
This assumption models the verified backend boundary only; it proves no JWT,
gateway or production authentication. B01 remains open. No separate permission
code is tested: the SQL authority is the active institution-admin role.

Call immediate(RB,B,U(2),reason) and reject(RB,B,U(2),reason), separately from
the same baseline. Both expect42501 with EXACT diagnostic
'Phase 8.1: active institution administrator required' from
phase81_assert_institution_admin(U(2),B), before request mutation/lookup.
Use T1 exact code AND origin capture. A positive rollback control for the SAME
actor U(2) with R(1),A must pass the admin guard; an independent control with
U(3)/H(3) admin B and RB,B must pass it too. Inspect actor/request state to rule
out inactive identity/tenant/role or missing service claims as the cause. Source:
[guard:132–165](../../../supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql#L132),
[immediate guard-before-lookup:535–550](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L535),
[reject guard-before-lookup:747–753](../../../supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql#L747).

After each denial, RB and all other membership rows, students/users/Auth,
user_roles/user_permission_grants, institutions, invitations/operations,
outbox/attempt/events and every audit table retain identical IDs/contents/times;
decision fields stay NULL and no new grants exist. No SQL security audit is
inserted by this guard; auth_security_events delta0 alongside admin/platform/
lifecycle audit delta0. Do not invent a required audit insert or claim an HTTP
security-event outcome. Snapshot after nested recovery BEFORE outer rollback,
then verify full restoration separately. Unexpected lookup-miss, success or
other42501 origin fails A. T1/C; all checks remain NOT RUN.

**T19 lookup-miss control is separate.** Bind existing R(1) in A but supplied
tenant B and verified active B-admin U(3)/H(3) claims. The administrator guard
passes; immediate(R(1),B,U(3),reason) returns exactly {not_found:true}, and
reject(R(1),B,U(3),reason) returns NULL. Both preserve the same full state baseline
with audit delta0. These are not evidence of tenant-boundary authorization denial
and cannot substitute for the U(2)/RB,B variants above.

No runtime result, owner decision or execution authorization is created by this
matrix. Legacy exposures, incomplete consumer fixtures, unavailable runtime
components and B01–B07 keep acceptance blocked even if offline checks pass.

