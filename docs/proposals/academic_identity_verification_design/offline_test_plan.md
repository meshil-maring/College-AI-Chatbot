# Revised offline specification test plan

Scope: proposal-only, synthetic, sequential specification and static boundary checks. Existing profiles/rosters remain unchanged and unverified absent independent current positive evidence. No SQL, application tests, migrations, hosted Supabase, live data or network access is used.

`draft_tests/contract_oracle.py` models explicit individual permission history, approved source custody/entries, decisions, separate candidate findings and a future current-state read rule. Its custody methods are **specifications of a separately reviewed trusted writer**, not implemented RPCs. Server hashing uses synthetic byte strings; it proves neither institutional authenticity nor private storage immutability. Dataclasses/deep copies express retained evidence, not database immutability.

Requester requirements, formal owner policy, model evidence and PostgreSQL evidence are separate. All policies, mandates and `SubjectBinding` records in fixtures are synthetic. No institutional approval or implementation approval is implied. The oracle can model a positive using synthetic trusted binding evidence; the SQL deliberately refuses all new positives pending design of the actual binding control. Offline success must not be described as SQL/DB feature completion.

## Run only these draft tests

From the project root, using the existing local interpreter, without application test configuration, bytecode or cache files:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s docs/proposals/academic_identity_verification_design/draft_tests -p 'test_*.py' -v
```

Do not run SQL or remove the intentional execution stop to run these tests. Report the actual command, count and result only after executing it. No test result establishes SQL validity or PostgreSQL behavior.

## Earlier revision evidence before the subject-binding correction (2026-10-17)

Working directory: `F:\Git Project\CollegeAIChatbot`. Exact command executed:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s docs/proposals/academic_identity_verification_design/draft_tests -p 'test_*.py' -v
```

Three runs during revision: **83 tests / OK**, then **85 tests / OK** after strengthening self-approval coverage and adding guards, then **85 tests / OK** after retaining candidate actor/Auth/time/permission provenance. All exited 0, with zero failures or errors. The final run reported `Ran 85 tests in 0.225s` and `OK`. Test methods with subtests are counted once by unittest; this is not 85 independent PostgreSQL/security checks. `-B` avoided bytecode; no result/cache artifact was created.

Those historical counts predate the corrected binding invariant. Independent review reproduced two false-positive model paths despite that suite passing. They are not evidence that subject-to-account ownership was enforced. Current subject-binding revision evidence is recorded separately below.

Only synthetic sequential model tests and text-based static guards ran. No SQL, migration, database integration test, hosted Supabase access or application test ran; no PostgreSQL security, constraint, authorization, locking, transaction or durability behavior was validated. These results cannot establish institutional authenticity, approved policy, real subject-binding completeness, private storage guarantees or audit immutability/retention.

## Revised sequential cases

| Area | Cases and intended assertions |
| --- | --- |
| Custody | Compute SHA-256 from synthetic original bytes; retain immutable-version reference, available issuer name/version/date, actor/Auth/mandate, upload time, exact locator and raw strings. Missing issuer metadata is NULL plus attested reason, never invented. Reject client digest, unaccepted/wrong-tenant source, unexplained missing metadata, invalid supplied date, absent authenticity method/provenance/evidence, noncustodian/revoked mandate, incomplete entries and duplicate keys/locators. |
| Authorized upload | Same-institution active staff/admin plus explicit uploader mandate and matching source uploader user/Auth snapshots; missing/wrong-tenant/revoked mandate or forged actor pair refuses acceptance. This does not test an upload service. |
| Required identifiers | Register number/person key mandatory; roll optional. Source values cannot be replaced/omitted in a positive request. Leading zeros/raw values survive. Numeric values and unknown kinds/rules are refused. |
| Policy | No policy, missing governance approvals, missing normalization/freshness, stale policy, mandatory roll configuration or unreviewed rule/person-key change blocks positive verification and permission grant. Synthetic bounded/no-expiry examples are alternatives for tests, never owner decisions. |
| Explicit permission | Separately assigned staff and admin succeed. Role/admin/wildcard/permission strings alone, wrong tenant, inactive account/role/tenant/Auth pairing, multi-scope ambiguity and disabled capability fail. Grant events retain exact code, institution, target, grantor/Auth/mandate, timestamp, role snapshot and reason. Corrupt/incomplete provenance refuses. Admin plus owner grantor mandate required to delegate; self-grant/revoke prohibited. |
| Binding ownership/self-approval | Every positive requires the exact structured proof receipt and attributable current approval for its institution/person/source/entry. Account mode requires a selected profile and matching active directory/profile user/Auth/association-revision tuple. No-accounts mode permits no selected profile or directory association. Subject, proof establisher, reviewer and verifier must be distinct by user AND Auth in the conservative model. Actual institutional authorities/proofing rules remain unresolved. |
| Revocation | Target inactivity/missing new policy do not obstruct revocation. Permission revision conflict refuses stale management. Revoked verifier cannot retry old decisions. Revoked grantor mandate prevents management but does not silently undo prior assignments. |
| Comparison | Full entry values checked against actual profile/roster register and roll fields; omitted source roll cannot hide a candidate roll. Roll-only/student-number-only links, duplicate candidates, split identifiers, conflicting roster links and ambiguous entries fail without first-match selection. Same canonical identifiers in another institution are independent. |
| Lifecycle | Candidate rejected/unresolved findings acquire no claims and never change established ownership. Reverification appends history; changed values require explicit correction. Person-key/profile reassociation and historical identifier transfer remain refused. Withdrawal works after source invalidation/missing policy, retains links/evidence, and cannot carry new register assertions. |
| Source incident | Invalidation needs custodian authority without new positive policy. It makes dependent evidence unusable in the future projection without erasing evidence/claims. Historical retry remains historical; new checks on that source fail. |
| Replacement/history | Accepting a second version retains the original source, decisions and claims without automatic transfer, overwrite or revocation. Invalidation retains incident actor/Auth, time, reason and evidence; explicit withdrawal retains prior positive evidence. A revoked verifier cannot withdraw. |
| Ambiguity/unresolved policy | Numeric, formula or OCR ambiguity refuses even when strings are supplied; only confirmed original strings are accepted. ASCII mechanisms do not invent Unicode normalization/confusable rules. Missing freshness or normalization approval raises `UnresolvedPolicy`; historical reuse after withdrawal reports unresolved owner policy rather than approving transfer. |
| Revisions/retries | Same request/key produces one modeled event/audit; changed payload conflicts; stale heads never rebase. Old positive retry reports newer head after withdrawal. No simulated transactions or concurrency. |
| Legacy/eligibility | Legacy input dictionaries stay unchanged; approval/roster state alone creates no identity. Future projection specification rechecks positive head, policy, source invalidation, expiry and later legacy conflicts. Expiry does not silently release claims. No invitation/token/account/role/email effect. |
| Static boundaries | Exactly seven artifacts, stop before DDL, no forbidden legacy writes or configuration seeds, no existing-function replacement, no application/DB/network imports. SQL substrings are review guards, not a parser or privilege proof. |

## Coverage limits and later application work

The oracle does not exercise PostgreSQL syntax, FK enforcement, ACL/RLS, inherited/default privileges, trigger behavior, table/row/advisory locks, concurrency, commit/rollback, disconnect durability or SQL byte-size semantics. Python rejection-before-state-change assertions are model behavior only. `postgres_integration_tests.md` lists the separate disposable-local tests; none are run by this suite.

Custody authenticity procedures, original-file parsing/OCR, object read-back integrity checks, upload limits, storage versioning/retention and actual authorization middleware require separate implementation and tests. Uploader/authenticator separation, correction dual-review, normalization format details, freshness/source supersession, identifier reuse, retention and lock budgets remain owner blockers. The synthetic fixture's policy references cannot resolve those decisions.

The oracle does not validate evidence contents, subject-association completeness or real reviewer authority. Its trusted binding fixtures attest account associations (including absence); they are not discovered from a real register. It checks sequential grant/revoke ordering only. Concurrent grant/revocation, stale snapshots, revocation lock ordering, transaction atomicity, SQL validity, constraints, ACL/RLS and audit protection all require the future PostgreSQL plan. Full character rules, source-age freshness and reuse/adjudication policy cannot be inferred from the normalization/expiry examples. Retention, deletion, backups, legal holds and exceptional evidence/audit access are also unresolved; an append-only Python history does not validate them.

## Subject-binding adversarial coverage

The normative invariant is in `rpc_contract.md`, **Exact subject-binding invariant**. `AccountAssociation` is a trusted current directory snapshot; `BindingEvidence` is a structured receipt of an already inspected institutional proofing/authentication procedure or complete absence search; `SubjectBinding` records a separately authorized approval of that exact receipt under the latest policy. The evidence registry, authority directory, explicit method/mode allowlist and establishing/reviewing mandates are synthetic trusted fixture inputs. A reference string, copied identifier or account name does not create those records. No real registrar check, authentication/proofing service, directory completeness check or owner approval is implemented.

`install_binding` deliberately creates a synthetic proofing receipt and calls the separate approval specification. Constructing a profile does not create evidence. Existing successful profile-link tests now explicitly provision consistent account evidence; their original identifier/conflict/history assertions remain. The source-acceptance test helper separately provisions fresh binding proof/review for source-change tests; `Oracle.accept_source` itself never establishes ownership. Fixture validity endpoints and independence rules are examples, not approved institution policy.

The adversarial class applies negative ownership cases to **verify, reverify and correct**. Its shared assertion checks rejection, unchanged identities/history/heads/claims/historical owners/receipts/successful audit events and unchanged profile inputs, an attributable separate denial event, and actual `current_usable=False`. Negative approval cases assert no new binding/history/successful audit and denial attribution. Existing historical decisions are retained, not rewritten. Matrices cover:

| Scenario | Required result |
| --- | --- |
| Both review probes | No-accounts receipt with a selected profile refuses, whether or not a directory row exists. Account B proof with account A profile refuses despite identical register/roll values. |
| Missing ownership | Missing profile user/Auth/revision, absent trusted directory, missing register with matching roll all refuse; identifier agreement never supplies ownership. |
| Wrong scope or evidence | Foreign institution, missing/altered/unregistered receipt, wrong person/source/entry, incomplete or contradictory mode/account fields refuse. |
| Freshness/revocation | Evidence validity boundary, revoked evidence/approval, revoked establishing/reviewing authority and absent method/mode/policy configuration refuse. No-accounts mode needs explicit synthetic allowlisting. |
| Association drift | Directory person/profile/user/Auth/institution/revision/activity changes after collection refuse new positives. Profile account/Auth/id/institution/revision changes after verification make the existing head unusable without changing history. |
| Reassociation | Even a consistent new account tuple with new approved evidence cannot transfer an existing positive via reverify/correct. Ordinary correction cannot attach an account to a historically unlinked positive. Missing historical binding snapshots cannot be upgraded by ordinary commands. |
| Independent authority | Unmandated admin, forged reviewer Auth, wrong/revoked mandate or wrong scope cannot approve. Subject-as-reviewer and verifier self-approval refuse; positive-operation matrices assert actual state, not only error text. |
| Historical reads | Account drift leaves an unchanged-key authorized retry historical and without new writes; current usability is false. Reapproval alone cannot refresh a prior positive; explicit new verification for the unchanged tuple is required. |
| Consistent positives | All three operations succeed only with explicit internally consistent proof, reviewer authority, active association and profile; retained tuple/history and true current usability are asserted. Account-independent positives require explicitly permitted no-account evidence and no association. |

`denials` models a separate restricted security-event path. It is excluded from the unchanged successful-domain/audit assertions because refusal must still be attributable. It is not a simulation of PostgreSQL denial-audit durability or transaction rollback. Read projections return false without rewriting decision status. Model input copies and sequential checks do not establish collection-to-commit atomicity; all real account/evidence writers must join a final reviewed locking/revision protocol before SQL positives could ever be considered.

The SQL guard test now checks the refusal's placement at the start of the non-withdrawal branch and the earlier historical-replay return, in addition to the pre-DDL stop. This remains a text check, not a SQL parser or proof of PostgreSQL control flow/security.

## Subject-binding revision results (2026-10-17)

Only this offline command was executed, from `F:\Git Project\CollegeAIChatbot`:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s docs/proposals/academic_identity_verification_design/draft_tests -p 'test_*.py' -v
```

Revision runs: **103 tests / OK**, **110 tests / OK**, then **111 tests / OK**. Each exited 0 with zero failures/errors. The final run reported `Ran 111 tests in 0.632s` and `OK`: **111 passed, 0 failed, 0 errors, 0 skipped; no remaining failures**. The original 85 test methods remain; 26 adversarial methods were added, with operation/scenario subtests counted within their parent methods. Successful profile fixtures now supply explicit consistent proof; existing rejection, identifier, revocation, history and withdrawal assertions were retained or strengthened.

Both independent-review false-positive scenarios are rejection/usability assertions in the suite, across all three new-positive operations; no separate probe script was run. Additional tests reject malformed registered receipts before approval, account/Auth sharing across subjects, ordinary account attachment/replacement and legacy positives without binding snapshots. Refusals preserve successful domain/history/audit state and retain separate denial attribution. Positive cases assert actual retained account identity, expected revision and current usability.

No SQL, migration, application test, PostgreSQL integration test, database or hosted Supabase operation was run. Both SQL stops and historical replay remain intact; the SQL file received comments only. Offline success does not prove real subject ownership, proof/session provenance, directory completeness, storage/audit controls, concurrency or any PostgreSQL security/behavior. The proposal/model is ready for another independent design review with owner/technical blockers; final design approval and implementation remain blocked.

Later application tests should follow existing authorization/audit/attendance conventions and prove that actor/scope/time/hash/official values cannot come from public requests, exact individual-grant provenance is enforced beyond generic wildcard matching, negative findings cannot alter a positive head, reads are tenant-safe/redacted and source objects never enter publication/RAG. Approval, roles, credentials, email verification and legacy rows must remain unaffected.

## Persistent no-accounts directory revision (2026-10-17)

The earlier 111-test run above predates this change. `rpc_contract.md`, **Persistent no-accounts directory invariant**, defines the proposed control: absence receipts now retain an exact `directory_baseline_id` and institution-wide `directory_generation`. Per-account association revision stays NULL in no-accounts mode. `DirectoryBaseline` is an explicit structured synthetic upstream completeness/history attestation with a live dedicated writer mandate; it cannot be created from an empty map or a provenance string. No real directory discovery, completeness proof or owner appointment is provided. Complete policy now requires an explicit synthetic `absence_directory` governance reference in addition to the existing requirements.

The sequential directory writer advances generation on every change, retains full prior snapshots as tombstones, and checks expected generation, actor/Auth/mandate/scope, timestamps and association revisions. It cannot reset an existing directory or reset account association revisions to make a historical account tuple usable again. A separate retained highwater, consecutive journal and exact head/live snapshot are mandatory. Missing/unreliable state refuses. An unchanged apparent directory cannot renew an old generation. No ordinary update clears an incident. Consistency checks over Python records do not prove durable anti-rollback or detect coherent rollback of all trusted stores; a real trusted external continuity/restore guarantee remains a prerequisite.

`NoAccountsDirectoryTests` exercises the following. Applicable matrices cover **verify, reverify, correct and current usability**. Each negative decision case asserts the exact intended reason code, matching registered receipt/approval preconditions, unchanged decisions/heads/history/claims/historical owners/receipts/successful audit and binding/directory history stores, one fully attributed denial, and actual false usability without domain writes. Detected directory integrity/completeness failures intentionally latch a separate `directory_unreliable` security marker, including on current reads. This security side effect is excluded from unchanged-domain assertions and explicitly checked; it models neither durable incident delivery nor a database read transaction. Existing positive heads are first asserted usable before a lifecycle change. Initial verification has no prior positive to preserve.

| Case | Required result |
| --- | --- |
| Complete, authorized baseline and unchanged generation | All three positive operations succeed, retain baseline/generation, preserve NULL account association revision and produce true current usability. |
| Association creation, then deletion | Old absence receipt refuses after creation and after deletion; retained journal includes the removed association; generation never returns to the receipt value. |
| Reassociation away from the original subject | The original subject has no current association, but its prior receipt still refuses on generation mismatch. |
| Recovery/replacement followed by removal | Replacement user/Auth/profile and later empty directory do not restore old proof. Even recovery with identical empty values advances generation. |
| Conflicting legacy record removal | Old proof refuses while the profile exists and after both directory/legacy records disappear, specifically on directory invalidation rather than identifier conflict. |
| Change-away-and-back and rollback | Equal initial/final rows have different generations. Rewinding journal/head to the old generation conflicts with retained highwater and refuses. Lost history cannot be reinitialized while continuity markers remain. |
| Inactive and historical associations | A fresh generation-matching receipt cannot bypass an inactive current association. A previously associated subject remains blocked even after deletion and fresh review, pending an owner-approved workflow. Receipt approval alone is not positive eligibility. |
| Missing/unreliable state | Missing head, history, highwater, bootstrap receipt or baseline; incomplete/history-incomplete, reference-only or foreign baseline; unresolved incident, history gap, boolean generation and untracked rows all refuse with their intended condition and latch unreliability. Deleting observed untracked rows or restoring missing history cannot clear that latch; tests cover command-side and read-side detection. |
| Registered invalid generation/baseline | Mutate the retained receipt, current binding and approval registry consistently; missing/noninteger/wrong generation or baseline refuses at generation validation, not registry-equality rejection. |
| Authority and policy | Unmandated/forged/wrong-scope/revoked writer, stale generation and foreign snapshot writes preserve state and add a denial. Writer revocation and missing `absence_directory` governance block new positives and usability. |
| Approval/replay/scope | Old receipt cannot obtain a replacement approval after change or lost history. Authorized historical replay creates no writes and remains unusable. Another institution's directory changes do not advance local generation. |
| Legitimate renewal | After an unrelated subject changes within the institution, the old proof refuses; fresh independent evidence/approval alone does not refresh history. An explicit new positive for the unchanged tuple can adopt that current generation. |
| Account protection | A directory writer cannot reset an account's historical association revision; proper recovery with a higher revision still leaves the old account verification unusable. |

The fixture's account helper now records explicit synthetic directory changes; constructing a profile still creates no proof. It chooses a fresh revision only for positive fixture setup when none is supplied; adversarial lifecycle tests pass explicit rows/revisions directly to the writer. The original no-accounts/selected-profile probe uses the writer for removal and asserts `binding_no_accounts` explicitly, so newly introduced continuity checks do not accidentally mask that original property. Existing tests/assertions remain.

Trusted directory writer/revision authority, complete authoritative coverage and alias inclusion, genesis/restore/anti-rollback guarantees, tombstone retention, generation granularity and costs, every-writer coordination, incident detection/reliability marking/evidence invalidation and previously-associated-subject recovery rules remain **unapproved owner decisions**. The model's conservative refusals do not approve those workflows. No SQL tables/writer/resolver, application changes or actual operational completeness/continuity are supplied. Both SQL refusals remain; the SQL revision is comments only. PostgreSQL/storage/application behavior remains unverified.

### Executed offline results for this revision

Date: **2026-10-17** (Asia/Calcutta). Working directory: `F:\Git Project\CollegeAIChatbot`. Exact command for each run:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s docs/proposals/academic_identity_verification_design/draft_tests -p 'test_*.py' -v
```

Development runs: `Ran 129 tests in 0.517s` / `OK`, then `Ran 134 tests in 1.233s` / `OK`. After adding persistent observed-integrity latching and bootstrap receipt coverage, the final run reported **`Ran 136 tests in 1.015s`**, **`OK`**, exit code **0**: **136 passed, 0 failures, 0 errors, 0 skipped**. The original 111 methods remain; **25 focused directory test methods** were added, with operation/scenario subtests counted within their methods. No failing test run occurred during this revision. No test/result/cache artifact was created; this narrative records the tool-reported result rather than a separately retained transcript or artifact digest.

Validation is strictly offline: only these synthetic sequential Python tests and existing text-based static guards ran. The seven existing proposal artifacts are the only edited files; SQL changes are comments only, and both unconditional refusals were retained. No SQL/migration/application or database integration tests, hosted Supabase/database operations, B05/E23 edits, deployment, commit or push occurred. No PostgreSQL security/behavior, durable directory/evidence/incident history, real completeness/proofing, storage or application behavior has been validated. Ready for independent review of the revised model and explicit blockers; **not ready for final design approval or implementation**.

## Strict-head and restoration hardening

The 136-test evidence above predates this revision. `_checked_directory_state` now independently validates the head generation using actual positive-integer type/range checks before equality. Journal, highwater, receipt and expected writer generations each require actual positive integers too. Booleans and floating/numeric substitutes cannot authenticate a snapshot via Python equality. State faults latch an integrity marker; an invalid receipt or expected request generation by itself does not contaminate a reliable directory. Bootstrap refusal now has its own attributed `directory_initialize` denial; these are synthetic sequential security events, not durable audit or a real time/authentication source.

Fifteen focused methods were added to `NoAccountsDirectoryTests`; all 136 earlier methods remain. Applicable negative matrices use verify/reverify/correct and current-usability assertions. They keep registered receipt and approval stores consistent, check the intended exact reason, unchanged decisions/heads/history/claims/historical ownership/receipts/successful audit and binding/directory history, attributed denials and the separate integrity marker. Read-only projection detection means no domain writes or decision denial; the explicitly documented security latch may change.

| New case | Intended condition and assertions |
| --- | --- |
| Head-only generations | Independently corrupt only the head with `True`, `False`, `"1"`, NULL, -1, 0, 2 and 1.0. Leave journal/highwater/baseline/receipt intact; new positives refuse, usability is false and integrity latches. A separate test detects each through a current read before any decision attempt and proves that repairing the head cannot clear the incident. |
| Other generations | Independently corrupt each journal/highwater/registered receipt generation with the same cases. Receipt/approval registries agree so the intended check is reached. State faults latch; receipt faults refuse without creating a directory incident. Invalid expected writer generation preserves state, produces a fully attributed revision-conflict denial and does not latch a healthy directory. |
| Collection chronology | A consistently registered current-generation receipt collected at source acceptance (20), before directory state (25), refuses specifically at directory-state chronology after source/evidence validity checks pass. |
| Ordinary restoration | Restore a previous empty snapshot and separately restore an identical empty snapshot as the sole invalidating event. Assert actual acceptance, exact generation +1, retained history prefix/tombstones, writer/Auth/mandate/time and successful audit; old proof refuses and current usability is false. No backup operational guarantee is inferred. |
| Independent highwater rollback | Leave journal/head intact and rewind only highwater; refusal latches. Putting the correct highwater back does not clear the marker. |
| Mixed restoration | Ten selected combinations restore head, journal, highwater, baseline, live rows and/or consistently registered old receipt. Assert exact history/snapshot/absence refusal and preserved domain/successful audit. The baseline is immutable and may be unchanged in a restored copy; copying it does not authorize a stale receipt. This is focused coverage, not every possible corruption combination. |
| Coherent total restore - characterization | Save a usable oracle, record creation/removal and a refused positive, then deliberately restore **every** model-held input including decisions/claims/receipts, audit, denials and incidents. Expect true current usability, historical replay with no writes and exact equality with that earlier state. The test intentionally shows that invalidation/history/audit are not durable against privileged total rollback. No detection or denial for an undetected event is claimed. A separate synthetic externally supplied unreliability signal then forces refusal and preserved restored domain state. |
| Ordinary operations after latching | All eight writer operations, including restore/remove/recovery, refuse on the existing integrity marker after the head is repaired, with valid authority/expected generation. Assert full attributed denial, unchanged success state, false usability and retained marker. |
| Bootstrap/cleanup after latching | After observed history loss, remove other directory markers and rows while retaining valid baseline/authority and the incident. Bootstrap refuses specifically on reset prohibition, adds an attributed bootstrap denial and changes no success state. Ordinary reconstruction cannot clear the marker. |
| Remove/recreate | Assert exact increments through create, remove, recreate with higher account revision and remove again. Old proof stays invalid; fresh proof still encounters retained association history and requires an owner workflow. |
| Reassociation variants | Start from current, explicitly verified usable absence evidence at generation two while an account belongs to another subject. Reassociate to the checked subject with the same account, another user/account/profile, or only a different Auth ID. Independently assert generation +1 and preserved history/audit/decision state before checking old-proof refusal/usability. The setup is not already stale. |
| Recovery/replacement and legacy cleanup | Assert exact independent increments for creation, recovery/replacement and removal. Refuse old proof before and after conflicting legacy rows disappear. The helper proves each accepted transition; stale-proof rejection alone is not counted as proof of advancement. |

The transition helper separately checks accepted writer generation/history/audit and protected-domain invariants **before** any negative decision assertion. The total-restore characterization is deliberately different: privileged rollback restores historical domain/audit/denial state, so that case cannot claim those later records survived. It is evidence of a model limitation, not a protective security check.

### Trust prerequisites and unresolved owner decisions

| Boundary | What the offline suite does | What remains unresolved and unvalidated |
| --- | --- | --- |
| Synthetic model | Strict types, retained-state consistency, exact binding/permissions, writer increments, refusal/denials and incident latching | No database, process authenticity, durable state, locking or operational guarantee |
| Trusted writer | Checks synthetic current actor/Auth/mandate and expected generation | Named directory/revision authority; every writer, alias, external identity, recovery and legacy flow covered; real authorization and transaction protocol |
| Persistent history | Retains sequential snapshots/tombstones and historical association revisions | Durable append-only history, deletion/retention/access rules and complete history from the approved baseline |
| Completeness | Requires a separately registered structured baseline attestation | Authoritative systems/coverage, inspected evidence, alias/account inclusion and trustworthy absence-search procedure; no completeness inference from a dict or reference |
| Durable continuity | Rejects detectable partial/mixed rollback | Independent continuity evidence across backups/restores, rollback/loss detection and fail-closed handling when authority/continuity cannot be established; no witness is supplied |
| Incident/recovery | Separate marker latches; ordinary updates/bootstrap cannot clear it | Who detects/reports incidents, durably records them, invalidates evidence, approves recovery and re-establishes trusted state; no incident-clear policy or recovery endpoint is approved |

Existing binding establisher/reviewer appointments, independence, freshness/source replacement, normalization/person-key stability/reuse, reassociation/account recovery, and evidence/audit retention/deletion/access responsibilities also remain owner decisions. An external unreliability flag in a fixture is not an independently trusted external continuity mechanism. The model cannot detect an entirely unobserved out-of-protocol change cycle or coherent restoration of all trusted inputs. Production unknown continuity must fail closed through the eventual authoritative boundary; both SQL refusals remain intact meanwhile.

### Strict-head/restoration revision results (2026-10-18)

Working directory: `F:\Git Project\CollegeAIChatbot`. Only the existing offline unit-test command was run:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s docs/proposals/academic_identity_verification_design/draft_tests -p 'test_*.py' -v
```

Actual tool-reported output: **`Ran 151 tests in 4.864s`**, **`OK`**. Exit code **0**; **151 passed, 0 failures, 0 errors, 0 skipped**. This revision had one test run, with no failures; method subtests are counted within their parent methods. All 136 preceding methods remain, with 15 added methods. Passing includes the explicit undetectable-total-rollback characterization; it must not be described as detection, durable continuity or a production security guarantee. This narrative is the retained run record; no new output/cache/transcript file was created.

Only the seven existing proposal artifacts changed; SQL edits are comments only. No SQL/migrations, application/PostgreSQL integration tests, database/hosted Supabase operations, B05/E23 changes, application/configuration changes, deployment, commit or push occurred. Neither unconditional SQL refusal was changed. Ready for another independent proposal/model review, with owner/durable-continuity and technical validation blockers; **not ready for final design approval, implementation or execution**.

## Association-tuple and populated-restoration gap closure

This revision follows the 151-test run above. The head's association rows now receive independent schema/type/range/scope checks before any head/journal/live equality comparison. `_directory_rows` requires actual declared fields, bounded nonempty institution/person/profile/user/Auth strings, exact institution scope, positive integer revision excluding booleans and numeric substitutes, boolean active and unique profiles. `_checked_directory_state` checks required head fields, strictly types its generation/time and validates both head and retained journal associations before comparing them. Malformed authoritative state refuses through `_directory_state` and latches the existing integrity marker. Bad receipt/request data alone still does not establish state corruption.

Nine methods were added; operation/scenario subtests remain within their parent method counts:

| New method | Actual assertions |
| --- | --- |
| `test_head_association_revision_requires_actual_positive_integer` | Valid populated journal/live row revision is integer 1; independently set only head revision to True, False, 1.0, 1.5, numeric string, NULL, zero or negative. All three positive operations refuse `directory_snapshot`, latch, preserve decisions/history/claims/receipts/registries/successful audits and append exact attributed denial. Repair does not clear the incident or restore usability. |
| `test_false_and_zero_association_revisions_cannot_authenticate_each_other` | Additional malformed-state case explicitly demonstrates dataclass equality of head False and journal/live zero, then asserts schema refusal, latching, preserved state and false usability. Zero itself is invalid; the independent head-only False case above retains valid integer 1 elsewhere. |
| `test_head_association_fields_and_container_are_independently_validated` | Head-only NULL/blank/whitespace/nonstring/oversized identifiers, nonboolean active and malformed containers/rows refuse while other authoritative snapshots and evidence remain valid. All three positive operations assert the same preservation, denial, latching and usability outcomes. |
| `test_missing_head_and_association_fields_refuse_without_attribute_errors` | Delete each declared association field, including defaulted active, or each required head field, solely in a copied head. Assert intended refusal rather than attribute error, preserved state, exact denial, latched incident and false usability for verify/reverify/correct. |
| `test_well_typed_head_association_substitution_contradicts_valid_journal` | Substitute subject, profile, user, Auth, positive revision or boolean active using valid types; foreign institution also refuses. Assert exact history/snapshot refusal and preservation/denial/latching/usability outcomes with untouched journal/highwater/live/receipts. |
| `test_head_association_fault_latches_on_current_read_before_any_decision_attempt` | Begin with genuinely usable absence decision in a populated directory. Head-only boolean or missing revision yields false usability, latches with no decision-denial event and preserves all success state. Repair still refuses a new positive with attributed denial. |
| `test_invalid_absence_receipt_does_not_mark_valid_populated_directory_corrupt` | Consistently register a malformed receipt generation. Assert absence-specific refusal, preservation/denial/false usability and no integrity marker; the populated authoritative directory remains independently valid. |
| `test_populated_identical_restore_requires_fresh_revision_and_invalidates_absence` | Start with valid populated directory, current-generation absence proof and prior usable decision for reverify/correct. Restoring unchanged revision 1 reaches and refuses specifically at the restore association-revision guard; current prior decision remains usable after refusal. Restore revision 2 succeeds, increments generation 2 to 3, retains prior history/audits and all protected decision/claim/receipt state. Old evidence then refuses with false usability; no integrity incident is invented. |
| `test_populated_restore_of_prior_account_tuple_enforces_retained_revision_maximum` | Start populated at revision 1; replace with another profile/user/Auth tuple for the same subject at revision 4. Restoring the old account at revision 1 or 4 refuses specifically at the historical-revision guard, preserving all state with exact writer denial and no marker. Restore old tuple at revision 5 succeeds, increments generation 3 to 4 and retains both populated predecessor snapshots and audit history. Old absence evidence refuses and remains unusable. |

The populated fixture records a valid unrelated subject's account before collecting/reviewing current-generation absence proof. This ensures head-only corruptions are isolated and the first restore attempt is not masked by stale directory evidence. Writer restore tests call the trusted writer directly with valid actor/Auth/mandate, current expected generation, valid row schema and chronology; the exact `directory_association_revision` assertion proves they reach restoration-specific validation. Accepted transitions are independently checked before stale-evidence assertions. Snapshot preservation checks now represent actual dataclass fields and scalar types structurally, so missing-field faults and boolean/integer equality cannot undermine the assertions themselves.

### Association-tuple and populated-restoration revision results (2026-10-18)

Working directory: `F:\Git Project\CollegeAIChatbot`. Only the existing offline unit-test command was run, once:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s docs/proposals/academic_identity_verification_design/draft_tests -p 'test_*.py' -v
```

Actual output: **`Ran 160 tests in 9.958s`**, **`OK`**. Exit status **0**; **160 passed, 0 failures, 0 errors, 0 skips**. All 151 preceding methods remain and nine methods were added. There were no failing runs in this revision. This narrative is the retained result; no output/cache/transcript file was created. The run verifies only the sequential offline model and existing static text guards. It does not validate SQL/PostgreSQL, transactions, durable history, real directory completeness, identity proofing, storage or application behavior. The existing coherent-total-rollback characterization still passes by observing usable old evidence when every model-held trusted input is restored; it is not rollback detection.

Exactly five existing artifacts changed in this revision: `README.md`, `rpc_contract.md`, `offline_test_plan.md`, `draft_tests/contract_oracle.py`, `draft_tests/test_contract_oracle.py`. `proposed_migration.sql` and `postgres_integration_tests.md` remain unchanged; both unconditional SQL refusals are intact. No files/directories were created. No SQL/migrations, database/hosted Supabase operations, database/application integration tests, application/configuration or B05/E23 changes, deployment, commit or push occurred.

Owner decisions remain unresolved for authoritative directory completeness/alias coverage, every-writer participation and authority, persistent history/tombstones, external continuity across restoration, incident detection/durable reporting/recovery, identity proofing and independent reviewer authority. Existing normalization/freshness/reuse, recovery/reassociation and retention/access policies are also unresolved. No in-memory assumption or fixture is owner approval. Ready for another independent proposal/model review; **not ready for final design approval, implementation or execution**.

## Account-mode types and malformed-live-row correction (2026-10-18)

This revision follows the reported 160-test run. Account mode now checks the full authoritative directory before comparing live associations, and independently validates selected profile snapshots. Live collection routes by validated institution/profile map keys and validates local records before dereferencing fields. Missing attributes and malformed objects therefore refuse and latch through the documented integrity path. Profile/receipt/request validation remains outside authoritative incident marking; valid tracked changes can fail ownership without falsely marking their consistent directory corrupt.

Fifteen focused methods are added to `NoAccountsDirectoryTests`, with all 160 existing methods/assertions retained. Applicable matrices cover initial verify, reverify and correct; existing-head setups first assert true usability. The shared negative assertion checks exact refusal code, consistent receipt/approval registries, unchanged decisions/history/claims/historical ownership/receipts/successful audit and directory/binding stores, full denial attribution and false usability. Structural snapshots preserve actual record fields and scalar types. Initial verify has no historical positive; reverify/correct supply populated decision/claim history.

| New coverage | Assertions and path isolation |
| --- | --- |
| Live account revision types | Head/journal/profile/evidence remain valid at revision 1; mutate only the live revision to True/False, floats, numeric string, NULL, zero or negative. Require `directory_snapshot`, latching, preservation and refusal after repair. |
| Live activity types | Independently mutate only active to NULL, 0, 1, 1.0 or a string; require schema refusal rather than equality acceptance. |
| Live identifier schema | Individually invalidate institution, subject, profile, user or Auth string while all other fields remain valid; require authoritative refusal/latching. |
| Profile revision types | Directory/evidence remain healthy; malformed profile revision refuses specifically as `binding_profile`, leaves marker clear, preserves state and permits checking the valid original snapshot again. |
| Profile identifier schema | Independently invalidate institution/profile/user/Auth snapshot fields before ownership comparisons; assert exact profile refusal and a healthy directory. |
| Profile missing fields/objects | Delete each required profile field or supply malformed row/container values; no attribute/key/type exception substitutes for refusal. |
| Well-typed profile mismatches | Institution/profile selection mismatch reaches `binding_profile`; user/Auth/revision mismatch reaches `binding_account_ownership`, with no directory incident. |
| Untracked live tuple changes | Valid-type substitutions contradict the retained head or scoped map key, latch, preserve state and stay unusable after repair. |
| Valid tracked tuple changes | Apply the authorized writer first, assert generation/history/audit, then require stale proof to reach `binding_account_ownership` with no marker; this isolates ownership from integrity checks. |
| Missing live fields, both modes | Delete each declared association field, including institution/revision/active, from a copied live row only. Verify/reverify/correct refuse, attribute denial and retain the incident after repair. |
| Malformed live objects, both modes | Replace only the local live row with NULL, dict/list/tuple/string/integer objects; require the intended authoritative schema refusal. |
| Read-first faults and repair | Start with usable decisions in both modes; missing institution/revision, malformed object, boolean revision or numeric active makes a current read false and latches without decision denial. Repair stays unusable; subsequent decision adds exact attributed denial. |
| Registered malformed account receipts | Keep receipt/current-binding/approval registries consistent with each invalid association revision; require `binding_incomplete`, false usability and no directory marker. |
| Malformed writer payloads | With healthy authoritative account state, invalid proposed restore rows refuse without latching, preserve state and append a fully attributed writer denial; prior valid evidence stays usable. |
| Account historical replay after incident | After read-side detection of a missing live institution, authorized replay returns only its recorded decision, preserves domain/receipts/audit/denials and leaves current usability false. |

The tests use synthetic registered authority, proofing and directory coverage. They do not establish real directory completeness, writer participation, identity proofing, storage, durable history, independent continuity, PostgreSQL behavior or incident recovery. Those owner/technical blockers and both SQL refusals remain. Only the oracle, its test file and these three proposal documents are revised; SQL and the PostgreSQL integration plan remain unchanged.

### Account-mode/live-row correction results

Date: **2026-10-18** (Asia/Calcutta). Working directory: `F:\Git Project\CollegeAIChatbot`. Executed only the authorized offline command, once:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s docs/proposals/academic_identity_verification_design/draft_tests -p 'test_*.py' -v
```

Actual output: **`Ran 175 tests in 6.755s`**, **`OK`**. Exit status **0**: **175 passed, 0 failures, 0 errors, 0 skipped**. No failing run occurred. All 160 preceding methods/assertions remain and 15 methods were added; subtests are counted within their methods. The existing coherent-total-state rollback test still characterizes undetectable privileged rollback rather than durable continuity. No test output/cache/transcript file was created; this narrative records the observed tool result.

Exactly five existing files changed: `README.md`, `rpc_contract.md`, `offline_test_plan.md`, `draft_tests/contract_oracle.py`, `draft_tests/test_contract_oracle.py`. No files or directories were created. `proposed_migration.sql` and `postgres_integration_tests.md` remain unchanged, with both unconditional refusals retained. No SQL/migrations, database/hosted Supabase operations, application tests/code/configuration or B05/E23 changes, deployment, commit or push occurred.

Ready for another independent review of these focused model corrections. Final approval, implementation and execution remain blocked by owner decisions and future technical validation, particularly authoritative directory completeness/alias and writer coverage, persistent history, independent restoration/rollback continuity, incident authority and recovery, real identity proofing and reviewer authority. Existing normalization/freshness/reuse/reassociation and retention/deletion/access decisions also remain unresolved. Offline passes establish no production security or durable continuity.

## Four-finding correction validation (2026-10-18)

The latest independent review reproduced four further defects despite the 175-test pass: equal-but-malformed retained evidence copies, missing baseline fields escaping refusal/latching, nonstring profile identifiers reaching string methods, and boolean expected revisions/false-like profile selections passing command validation. This focused correction changes only the existing oracle, its tests and these three proposal documents. SQL and the deferred PostgreSQL plan are not edited.

Twenty-four added methods retain all 175 preceding methods/assertions. Shared negative checks preserve scalar types and missing fields without relying on malformed dataclass equality, assert unchanged retained domain/evidence/directory/receipt/successful-audit state, assert full decision-denial attribution, and distinguish a directory latch from malformed proof/request/snapshot input.

| Finding | Focused tests and limits |
| --- | --- |
| Retained evidence copies | `test_retained_proof_revision_is_validated_independently`, `test_retained_approval_revision_is_validated_independently`, `test_current_binding_revision_is_validated_independently` and `test_historical_head_revision_is_validated_independently` corrupt only one copy. True/False, integral/fractional floats, numeric strings, NULL, zero and negatives are tested independently. Applicable verify/reverify/correct commands refuse and current reads remain false without a directory marker. |
| Earlier history and other fields | `test_non_head_historical_revision_blocks_reads_and_new_positives` leaves a valid later head while corrupting the earlier snapshot. `test_retained_security_fields_are_checked_before_equality`, `test_each_retained_copy_requires_all_declared_fields` and `test_malformed_retained_copy_objects_refuse_without_directory_incident` cover malformed identifiers, completeness/time fields, deleted fields and malformed record/dictionary objects. `test_absence_generation_is_checked_in_each_retained_copy` tests boolean/float generation copies in no-account mode. |
| Preserved history/correction | `test_historical_replay_remains_history_only_after_retained_proof_fault` asserts authorized replay has no writes and cannot establish usability; a corrected proof copy alone does not require clearing a fictitious directory incident. `test_fresh_correction_preserves_expired_but_well_formed_historical_evidence` requires fresh valid evidence for the unchanged tuple while preserving expired historical evidence. |
| Authoritative baseline | `test_baseline_requires_each_declared_field_in_both_modes` includes missing institution/associations/writer identity and every other declared field across all three positive commands. `test_malformed_baseline_objects_refuse_and_latch_in_both_modes` and `test_baseline_field_types_refuse_before_authority_and_row_operations` check objects/types. `test_read_first_baseline_detection_survives_field_or_object_repair` asserts false reads, no decision denial on reads, persistent latch and attributed subsequent command denial after repair. |
| Request/evidence distinction | `test_request_or_receipt_errors_do_not_fabricate_baseline_detection` keeps an unrelated baseline fault present but refuses an earlier malformed command/proof without claiming the baseline was inspected or latching it. Existing healthy-directory malformed-writer/profile/receipt tests remain intact. |
| Profile/roster identifiers | `test_profile_identifier_types_refuse_before_string_operations` and `test_roster_identifier_types_refuse_without_directory_incident` cover integer/float/boolean/list/dict/tuple/bytes values in both register/roll positions. `test_missing_profile_register_stays_refused_and_null_roll_stays_optional` covers NULL/empty/whitespace register refusal and permitted NULL roll. `test_unselected_profile_identifiers_are_validated_in_both_modes` checks local unselected snapshots as well. |
| Command parameters | `test_decision_expected_revision_requires_actual_nonnegative_integer` covers verify/reverify/correct/withdraw with booleans, floats, strings, negatives, NULL and containers. `test_malformed_profile_selection_never_falls_back_to_retained_target` includes empty/blank strings, False/zero/containers and other malformed values. Refusals preserve otherwise valid current usability and do not latch corruption. `test_explicit_none_preserves_valid_retained_account_selection` checks permitted omission; `test_permission_expected_revision_also_rejects_boolean_substitutes` covers the equivalent permission-command check. |

Only the established offline command is used, with bytecode disabled and no output/cache files created:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s docs/proposals/academic_identity_verification_design/draft_tests -p 'test_*.py' -v
```

The first correction run reported `Ran 197 tests in 26.682s`, exit **1**, **3 failures, 1 error, 0 skipped**. The error exposed an introduced loss of the existing `UnresolvedPolicy` subtype for missing baseline bootstrap prerequisites; that subtype was restored. The three failures were new whitespace subtests expecting `identity_conflict` where the existing normalizer correctly returns `policy_or_identifier`; those new expectations were corrected. No preceding test/assertion was changed. Two additional cases then covered fresh correction with expired historical proof and request/receipt refusal before unrelated baseline inspection.

The final run of the exact command above reported **`Ran 199 tests in 44.656s`**, **`OK`**, exit **0**: **199 passed, 0 failures, 0 errors, 0 skipped**. Subtests count within their methods. Comparing the final test source with the pre-edit source after removing only the added block reproduced the original test file exactly: no existing tests, helpers or assertions were removed or weakened. The focused final diff against the seven originals retained in session memory shows exactly five changed existing files: `draft_tests/contract_oracle.py`, `draft_tests/test_contract_oracle.py`, `README.md`, `rpc_contract.md`, `offline_test_plan.md`. `proposed_migration.sql` and `postgres_integration_tests.md` are unchanged, including `DESIGN_ONLY_NOT_AUTHORIZED` and `AV_SELF_APPROVAL_CONTROL_UNRESOLVED`. No new files/directories, SQL execution, database/service/provider/deployment operations, application/configuration or B05/E23 edits, commit or push occurred.

The suite remains a synthetic sequential specification plus text guards. Real authority/proofing, complete directories/aliases, all writers, persistent history/tombstones, external restoration/rollback continuity, durable incident delivery and recovery, storage, PostgreSQL/security/locking and operational behavior remain unvalidated. Owner decisions remain required for freshness/source replacement, normalization/collisions/reuse, reassociation/recovery, retention/deletion/access/backups and named proofing/directory/recovery authorities. Coherent privileged rollback of every model-held trusted input remains undetectable without an independent witness. Neither SQL refusal is removed; final design approval, implementation and SQL execution remain blocked.
