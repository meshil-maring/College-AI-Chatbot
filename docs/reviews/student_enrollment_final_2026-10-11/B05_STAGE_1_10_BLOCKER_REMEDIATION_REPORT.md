# B05 Stage 1.10 blocker remediation

2026-10-12, Asia/Calcutta. Source changes and offline verification only.

**BLOCKERS REMAIN.** Preparation specifications have been expanded for another
independent review. Immutable runtime identities/components, legacy authorization
compatibility, consumer scope and all B01–B07 owner decisions remain unresolved.
No execution authorization is granted by remediation, rehashing or this report.

Baseline: [Stage 1.9 readiness review](B05_STAGE_1_9_INDEPENDENT_READINESS_REVIEW.md)
and [Stage 1.9 raw-byte evidence](B05_STAGE_1_9_OFFLINE_HASH_EVIDENCE.json), both
preserved byte-for-byte. All 52 declared raw SHA-256/length pairs matched at entry.
[Stage 1.10 entry snapshot](B05_STAGE_1_10_ENTRY_HASHES.json) records 80 relevant
files, including all migrations, pinned inputs, existing top-level validation
runners/guards, reset source, recovery contract and the two Stage 1.9 artifacts.
It does not inventory ignored files or establish deployed state.

## Changes and findings

Only four pre-existing preparation files changed:

- [test_matrix.md](../../../scripts/validation/b05_containment/test_matrix.md):
  T1 continuing INVOKER single-statement error subtransaction; T2 whole-file
  abort; T3 separately committed/concurrent steps; unconditional cleanup C and
  incomplete-run rule A; exhaustive expected-error inventory; detailed M01–M21
  fixture/operation/result/state/grant/audit/cleanup contracts. Every case remains
  NOT RUN. No executable SQL wrapper or derivative was created.
- [README.md](../../../scripts/validation/b05_containment/README.md): exact future
  runtime prerequisite/identity-verification contract and B01–B07 register with
  unresolved question, evidence, compatibility/security consequences, owner
  decision and safe source-work boundary per blocker. No owner or approval invented.
- [runner_contract.json](../../../scripts/validation/b05_containment/runner_contract.json):
  version3/stage1.10, linked T1/T2/T3 requirements, explicit unresolved component
  versions/identities, open decision register and assertion-failure INCOMPLETE
  acceptance semantics. Existing target, ownership, termination, cleanup and
  authorization safeguards retained; runtime_adapter, shim/supervisor, image/CLI/
  engine and derivative approvals remain NULL. FAILED_CLEANED remains a separate
  resource outcome, never a successful acceptance outcome.
- [migration_manifest.json](../../../scripts/validation/b05_containment/migration_manifest.json):
  rehashed the three changed inputs, marked stage1.10/unapproved consistency only.
  Exact ordered40 migrations and12 pinned input identities unchanged. Rehashing
  is not independent approval; the manifest itself is hashed in new evidence.

New review files: this report, entry snapshot, [offline verifier](verify_b05_stage_1_10_offline.py)
and [Stage 1.10 raw-byte evidence](B05_STAGE_1_10_OFFLINE_HASH_EVIDENCE.json). The
verifier reads local source/JSON/AST and writes its review evidence only. It
does not import/call prepare.py, preparation_plan(), main(), any runner or executor.

| Stage 1.9 finding | Source-level remediation / remaining limit |
| --- | --- |
| 1 Expected-error continuation | Specified nested EXCEPTION rollback around one tested statement at actual role, exact SQLSTATE AND origin, assertions outside catch, outer savepoint restoration, one S connection, unchanged ON_ERROR_STOP=1. Whole-file refusal and unexpected-error exit/rollback/cleanup separated. Implementation and independent PostgreSQL/runtime verification remain unavailable |
| 2 Incomplete acceptance oracles | Expanded all21 cases; detailed overload/self-assignment/scope-overwrite observations, typed identities/arguments, NULL versus error branches, stage/row/event outcomes and per-participant concurrency order. Short-lived +3-second server-clock expiry requires proved target-lock wait and release below5-second timeout; early NULL/timeout never counts as decision-time23514. Larger academic/attendance/test consumer fixtures in M20 remain unavailable and explicitly blocked; no invented acceptance |
| 3 Runtime immutable identities/components | Exact inherited PostgreSQL170006/vector0.8.0/btree_gist1.7 requirements preserved. New explicit NULL slots for CLI/Engine/API/Desktop/host/interpreter builds, binaries/libraries, startup/supervisor/adapter/fake/observer/config/probes. Endpoint/CLI/image verification specified; availability and approvals UNRESOLVED. No versions selected or tools inspected |
| 4 Retained legacy authorization | OPEN HARD BLOCKER. assign4 self-assignment and foreign-scope overwrite, create7 supplied-issuer trust and invite_approve7 supplied-decider/no-new-grant/no-decision-audit behavior specified distinctly from guarded new paths. Org-admin denial/full rollback versus desired compatibility remains owner decision; signatures/bodies/grants untouched |
| 5 Hash versus SQL refusal | Preparation oracle resolved: changed staging bytes refuse BEFORE CREATE/SQL, no SQLSTATE/ledger change. Catalog/ledger variants bind exact named SQL guard/P0001 and compare against tampered baseline after rollback. Ledger has no hash column; changed default expression/equal-count FK may evade SQL predicate and require independent full-definition comparison |
| 6 Maintenance regression | Source implication specified already in F/U: reset public noninternal TRUNCATE-trigger predicate matches B05 lifecycle guard before S. M15 evaluates only predicate/refusal, never reset script or destructive reset statements. B06 replacement/retention/consumer decision remains OPEN |

Source inspection also narrowed several distinctions that must survive re-review:
immediate/reject same-status retries preserve original actor/reason rather than
enforcing decide's stricter conflict rule; provider_created Auth-ID recording
does not itself validate an Auth row; accepted recovery does not recheck grant/
issuer revocation or expiry; trusted direct service GUC writes can bypass RPC
stage eligibility. These are source expectations/authority limits, not exploit,
deployment or PostgreSQL observations. No behavioral changes were made for them.

## Offline verification

All commands below used repository root `F:/Git Project/CollegeAIChatbot` in
PowerShell. `-B` prevents bytecode writes. No SQL/parser client, migration,
M01–M21, Docker/PostgreSQL service, engine endpoint, database/provider, secret,
deployment or push was used. No execution adapter was implemented.

```powershell
python -B -m unittest discover -s scripts/validation/b05_containment -p test_preparation_safety.py -v
```

Exit0, **9/9 PASS**, 0.066 seconds. Eight mocked path-denial/type/order checks and
one fixture uniqueness/canonical staff-linkage check. These do not run the
preparation plan or any runtime case and do not prove engine/path-race enforcement.

```powershell
python -B docs/reviews/student_enrollment_final_2026-10-11/verify_b05_stage_1_10_offline.py
```

Final exit0. Exact final output:

```text
PASS: 52/52 raw-byte hashes and lengths; 40/40 migration identities/order/declared transaction boundaries
PASS: 76/80 entry files preserved; 4 allowed documentation/contract/manifest changes
PASS: original stops and final rollbacks; successor copy byte-identical; ledger array exact
PASS: 21 detailed case specifications NOT RUN; 7 decisions OPEN; unresolved pins retained; no execution adapter
PASS: preparation AST/syntax and source anchors; runtime behavior NOT VERIFIED
WROTE: docs/reviews/student_enrollment_final_2026-10-11/B05_STAGE_1_10_OFFLINE_HASH_EVIDENCE.json
```

This verifier checks raw hashes/lengths, migration set/order/name/version/path and
declared transaction markers, entry-file preservation, active unconditional stops,
final rollback, successor byte equality, exact ledger array, textual M-case coverage/
status, JSON NULL approvals/safeguards, preparation syntax/import AST and selected
SQL source anchors. Textual coverage/anchors are consistency checks, not proof that
every oracle or PostgreSQL behavior is correct; an independent source re-review
is still required. The JSON hashes this report, entry snapshot and verifier; it
excludes its own hash to avoid self-reference. Externally hash it when approving
evidence. No self-authenticating approval claim is made.

Independent final evidence consistency command (after the verifier writes the
final JSON):

```powershell
@'
import hashlib,json
from pathlib import Path
p=Path('docs/reviews/student_enrollment_final_2026-10-11/B05_STAGE_1_10_OFFLINE_HASH_EVIDENCE.json')
e=json.loads(p.read_bytes())
for r in e['results']+e['preserved_entry_files']+e['new_review_artifact_hashes']+[e['manifest_identity']]:
    raw=Path(r['path']).read_bytes()
    assert (hashlib.sha256(raw).hexdigest(),len(raw))==(r['sha256'],r['bytes']),r['path']
assert e['runtime_cases']=={f'M{i:02}':'NOT RUN' for i in range(1,22)}
assert e['entry_changed_count']==4 and e['entry_preserved_count']==76
print('PASS: final evidence agrees with current pinned/preserved/review artifact bytes; M01-M21 NOT RUN')
print('Evidence SHA-256 (external, not self-embedded): '+hashlib.sha256(p.read_bytes()).hexdigest())
'@ | python -B -
```

Exit0; exact PASS line above returned, plus the current external JSON SHA-256.
That self-fingerprint is deliberately not embedded in this hashed report/JSON,
avoiding a circular report-to-evidence hash. The consistency command compares
final report/verifier/entry/pinned/preserved artifact bytes independently.

```powershell
git diff --no-ext-diff --no-textconv --exit-code HEAD -- scripts/validation docs/reviews/student_enrollment_final_2026-10-11/SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql docs/reviews/student_enrollment_final_2026-10-11/SECURITY_CONTAINMENT_POST_B05_SUCCESSOR_DRAFT.sql supabase/migrations scripts/maintenance/reset_supabase_data.sql backend/tests/B05_RECOVERY_CONTRACT.md
git diff --check
git status --short
```

Each command exit0. Tracked preservation diff and diff-check output empty.
Entry status was only the pre-existing untracked package and two Stage1.9 files.
Final status adds the four Stage1.10 review files; package remains untracked.
Tracked diff alone cannot detect untracked edits; independent80-file entry
comparison establishes the bounded preservation claim. Git warned that the user
global ignore file was inaccessible; it was neither inspected nor changed.

Important source inspection commands, with returned evidence:

```powershell
rg -n 'CREATE FUNCTION|CREATE OR REPLACE FUNCTION' supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql
rg -n 'CREATE.*FUNCTION|RENAME|RAISE EXCEPTION|ERRCODE|BEGIN;|ROLLBACK;' scripts/validation/b05_containment/containment_successor.validation.sql
rg -n 'users_auth_user_id_fkey|FOREIGN KEY.*auth_user_id|phase81_prevent_audit_mutation|ERRCODE' supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql
Get-Content -Encoding UTF8 scripts/maintenance/reset_supabase_data.sql | Select-Object -First 110
```

Exit0, source declarations/guards/FK and reset predicate returned. Full B05,
fixtures/bootstrap/preparation contract and relevant successor/legacy bodies were
read as UTF-8 source. No AGENTS.md was found by repository rg inventory or explicit
parent/root checks. One initial rg passed unexpanded Windows wildcard arguments
`supabase/migrations/20260917000000* supabase/migrations/20250717000000*`, returning
os error123; corrected explicit-filename query above succeeded. No verification
result depends on that failed search.

Entry hash command (exact original script; it must not be rerun now to replace
the historical snapshot with changed bytes):

```powershell
@'
import hashlib, json
from pathlib import Path
r=Path('.')
p=r/'scripts/validation/b05_containment'
m=json.loads((p/'migration_manifest.json').read_bytes())
b=json.loads((r/'docs/reviews/student_enrollment_final_2026-10-11/B05_STAGE_1_9_OFFLINE_HASH_EVIDENCE.json').read_bytes())
rows=[]
for e in m['migrations']+m['pinned_inputs']:
    raw=(r/e['path']).read_bytes()
    h=hashlib.sha256(raw).hexdigest()
    assert (h,len(raw))==(e['sha256'],e['bytes']), e['path']
    rows.append({'path':e['path'],'sha256':h,'bytes':len(raw)})
assert [(x['path'],x['sha256'],x['bytes']) for x in b['results']]==[(x['path'],x['sha256'],x['bytes']) for x in rows]
paths=set(x['path'] for x in rows)
paths.update(str(x).replace('\\','/') for x in (r/'scripts/validation').glob('*') if x.is_file())
paths.update(['scripts/maintenance/reset_supabase_data.sql','backend/tests/B05_RECOVERY_CONTRACT.md','docs/reviews/student_enrollment_final_2026-10-11/B05_STAGE_1_9_INDEPENDENT_READINESS_REVIEW.md','docs/reviews/student_enrollment_final_2026-10-11/B05_STAGE_1_9_OFFLINE_HASH_EVIDENCE.json','scripts/validation/b05_containment/migration_manifest.json'])
all_rows=[]
for path in sorted(paths):
    raw=(r/path).read_bytes()
    all_rows.append({'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
out={'stage':'1.10 entry baseline','runtime_status':'NOT RUN','stage_1_9_pins_match':52,'files':all_rows}
(r/'docs/reviews/student_enrollment_final_2026-10-11/B05_STAGE_1_10_ENTRY_HASHES.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(f'PASS: Stage 1.9 baseline 52/52 raw-byte pins match; recorded {len(all_rows)} entry files')
'@ | python -B -
```

Exit0, `PASS: Stage 1.9 baseline 52/52 raw-byte pins match; recorded 80 entry files`.

## Raw-byte hash changes and preservation

SHA-256 over Path.read_bytes(), no newline normalization. LF/CRLF differences
are part of raw hashes. Full new/old identities, bytes and all comparison results
are in Stage1.10 hash evidence; original Stage1.9 evidence remains unchanged.

| File within scripts/validation/b05_containment | Entry bytes / SHA-256 | Final bytes / SHA-256 |
| --- | --- | --- |
| README.md | 14428 / bd2a1c0f03102034b8c547e9da0a9f2910ac97cbdf6efb98b65fd1fff18d1a82 | 27419 / 69a4be6e7d94d49f6765dbf0fe4901ab63d45bef108c674a1eea3650a56ad952 |
| runner_contract.json | 12079 / 2604a54505765ad090084a2914a95000a34b10322f7912251488d0bc882f0a8d | 17754 / c18b23a093e21aea584e8f100fe733feffe690784db19741c245387523a3a278 |
| test_matrix.md | 25037 / 0a94d45d24abb4d6a45da2963f087dd1ee2cc575157c29b37520422c98b509a9 | 84107 / df11a19fc8f18c3b3fecfd61930657be52a06ed510c435f36b64ee05e474e4aa |
| migration_manifest.json | 24714 / f08d5a4f990e051fa952994bcad01628107e67c064530b7edd429ed0d431cc35 | 25314 / 76abfbb8679f31c7cbb8907a3262eb1141325cd88490c6d8240237dfea746bde |

All40 migrations and nine other pinned inputs unchanged. Preserved B05 migration:
53941 bytes, `581146602e75d94342777b81ee70b9ab423fb0117b2fda8b871d4b750249bc1e`.
Original candidate:49694 bytes, `897a4c786adc487bce04462690f8a4bbcab215f2e3e53841f84a82f40c1a63c7`;
active stops28/31, final ROLLBACK443, original11-column expectation unchanged.
Successor source and validation copy each51805 bytes,
`d360dd302c7be96e042d45d3056bd15934b107ab8c8de8ada9c113d2b8344d37`;
active stops42/45, BEGIN39/final ROLLBACK475, original12-column/40-version
conditions unchanged; no derivative or successor ledger version.
Existing shared guard:8322 bytes,
`2a7617a5f0771712fe816ff5dfe3b922e7294ab11553f45fc6bac5364bd5fcbe`.
All recorded existing top-level validation runner safeguards, fixtures/bootstrap,
prepare.py, reset and recovery source preserved. No unrelated change was altered.

## Remaining decisions and runtime status

All B01–B07 OPEN; owner identities/approvals UNRESOLVED. Image digest/content ID,
CLI absolute path/hash/version/build, engine ID/version/API/Desktop identity,
host/interpreter/tool/library/config identities, reviewed startup shim/supervisor,
adapter/mock evidence, SQL wrapper/derivatives, offline provider fake and independent
resource-release observer remain unavailable or uncollected. Larger consumer
fixtures/definitions and separate compatibility/retention/cutover decisions remain
open. Existing reference tag and synthetic bootstrap versions prove no availability.

M01–M21: **NOT RUN**. PostgreSQL/transaction/SQLSTATE/trigger/concurrency/cleanup/
provider behavior: **NOT RUNTIME VERIFIED**. No service started, no endpoint or
database connected, no secret inspected, no migration/SQL executed, no provider
called, no deployment/push. A further independent source re-review and separately
supported owner decisions/prerequisite evidence are required before any bounded
execution proposal. This successful offline remediation of specification gaps
does not authorize execution or close the remaining blockers.
