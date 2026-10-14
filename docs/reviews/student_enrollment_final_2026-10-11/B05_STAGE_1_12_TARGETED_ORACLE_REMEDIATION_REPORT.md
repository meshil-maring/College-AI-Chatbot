# B05 Stage 1.12 targeted oracle remediation

2026-10-12, Asia/Calcutta.

**TARGETED ORACLE FIXES COMPLETE — INDEPENDENT RE-REVIEW REQUIRED**

This verdict concerns exactly the three preparation specification findings. It
does not close runtime, legacy compatibility, consumer or B01–B07 blockers.
Every M01–M21 remains **NOT RUN**; no execution or collection is authorized.

Read before editing: [Stage 1.10 independent readiness review](B05_STAGE_1_10_INDEPENDENT_READINESS_REVIEW.md)
and the complete [Stage 1.10 remediation report](B05_STAGE_1_10_BLOCKER_REMEDIATION_REPORT.md).
The historical reviews/evidence remain unchanged. New
[entry snapshot](B05_STAGE_1_12_ENTRY_HASHES.json) records 118 existing relevant
source/package/review files after confirming all 52 entry pins. This is a bounded
local preservation inventory, not a deployed catalog or inventory of ignored files.

## Necessary changes

Only three pre-existing files changed:

- [test_matrix.md](../../../scripts/validation/b05_containment/test_matrix.md):
  OB12 source-backed outbox modes and all-case register; C12 complete direct/RPC
  cancellation state and timestamp contracts; T19 exact tenant-boundary and
  separate lookup-miss actor setups. Existing case statuses and T1/T2/T3/C/A remain.
- [test_preparation_safety.py](../../../scripts/validation/b05_containment/test_preparation_safety.py):
  three offline source checks validate actual outbox observation columns and
  terminal write set, kind-specific cancellation constraints/clock behavior,
  and fixture/guard ordering for tenant-boundary attribution. Original nine
  tests remain; total 12. These are source consistency tests, not SQL tests.
- [migration_manifest.json](../../../scripts/validation/b05_containment/migration_manifest.json):
  rehashed only those two pinned inputs and added targeted_oracle_revision 1.12
  with exact three-item scope and unapproved re-review status. Contract/package
  base stage 1.10 remains unchanged to preserve the runtime contract. Ordered
  40 migration identities and the 12 input identities/order remain unchanged.

New review artifacts: this report, entry snapshot,
[offline verifier](verify_b05_stage_1_12_offline.py) and
[hash evidence](B05_STAGE_1_12_OFFLINE_HASH_EVIDENCE.json). No fixture SQL, wrapper,
derivative, runner or executable runtime adapter was added or changed.

## Resolution of the three findings

| Finding | Specification resolution and source-supported limits |
| --- | --- |
| Terminal outbox oracles | OB12 captures all 18 actual outbox columns, matching IDs/aggregate, attempt_count, generated delivery_sequence and full attempt/event histories. OB12-T requires pending-row cancellation/token clearing/terminal category/Tsql update; non-pending and unrelated rows stay identical. OB12-I distinguishes accepted/terminal retries and historical repair; OB12-C/R specifies insertion and existing pending-only rotation. The OB12 register maps every M01–M21 operation/restoration to its required, forbidden or retry behavior. No version column or platform outbox is invented. |
| M12 cancellation timestamp | C12 binds valid invited state, null acceptance/terminal fields, synthetic identity/expiry, institution delivery fields and pending outbox. Complete direct cancellation changes status plus cancelled_at to the explicit validated fixture_anchor. RPC cancellation uses its own clock_timestamp, observed within server bounds. Status-only institution failure identifies the retained timestamp CHECK; platform has no equivalent CHECK. Identical direct/RPC retries and historical repair preserve the timestamp; arbitrary direct timestamp overwrite is not assumed forbidden. |
| M19 wrong-tenant actor | T19 binds active confirmed U(2)/H(2), admin only in A/OA, to RB=R(4) owner-restaged together to B/OB, preserving the existing request ID to avoid duplicate pending user/role requests. immediate/reject with RB,B,U(2) expect exact 42501 administrator-guard origin; independent valid controls rule out inactive roles/tenants, bad claims and missing EXECUTE. Full membership/resource/grant/outbox/audit snapshots stay unchanged, including auth_security_events delta0. Authorized B-admin U(3) with R(1),B is separately bound to not_found/NULL lookup outcomes. |

Source anchors are linked directly in OB12/C12/T19. Principal sources:
worker schema/terminal trigger at 7–51/112–128; webhook delivery_sequence at 6–10;
institution terminal-state CHECK at 66–91; actual Phase 7.15 delivery columns at
40–80; platform invitation schema at 8–29; B05 rotation at 452–514,
guard/lifecycle at 152–203/838–933; Phase 8.1 admin guard at 132–165;
B05 immediate/reject guard-before-lookup at 535–550/747–753.

Future synthetic setups are specified, not loaded. fixture_anchor supplies
deterministic explicit direct-UPDATE data; it does not freeze database clocks.
Tsql is independently observed transaction now(), and RPC cancellation bounds
observe server clock_timestamp(). No host-clock equality, monotonic version,
identity-sequence continuity/rollback, processing-delivery cancellation, JWT
verification, gateway identity or production consumer availability is assumed.
The processing-row token, historical-pending-row repair and mutable direct
cancelled_at limits remain explicit source limits within open decisions.
The rejected branch of legacy decide remains outside this three-finding scope;
no new tenant-denial promise is imposed on that different identity.

## Before/after raw SHA-256 and lengths

No newline normalization. Full comparison records are in the new hash evidence.

| Preparation file | Before bytes / SHA-256 | After bytes / SHA-256 |
| --- | --- | --- |
| test_matrix.md | 84107 / df11a19fc8f18c3b3fecfd61930657be52a06ed510c435f36b64ee05e474e4aa | 106301 / a654bf895a26acd8d5f19edb2535185925c36b532c79d26ecc54e6b50324a13d |
| test_preparation_safety.py | 7876 / 230a3ecf3abb0713d3b3afce7221430b93a945e7d8631d0bd93e1803748c737f | 14464 / 2e8a7f5ae269a1c056451e0587362063d527b7374e23964e40cfc05916fe4982 |
| migration_manifest.json | 25314 / 76abfbb8679f31c7cbb8907a3262eb1141325cd88490c6d8240237dfea746bde | 25694 / 52d1bfc38db7f1466b884cf8c971c75c44b44ebb77df1b54b08d5d49b0720208 |

The 115 other entry files are preserved, including all migrations, original
stopped drafts/copy, shared guard and top-level runners, prepare.py, bootstrap,
fixtures, README, runner_contract, maintenance source, backend source, recovery
contract, authorization annex and historical reports/evidence. Existing untracked
working-tree entries are retained; only the four Stage 1.12 review files are added.

## Exact offline commands and results

Working directory: `F:/Git Project/CollegeAIChatbot`, PowerShell. Python `-B`
prevents bytecode writes. Tests import preparation definitions but do not call
preparation_plan/main; the new verifier reads raw local files/JSON/AST only.

```powershell
python -B -m unittest discover -s scripts/validation/b05_containment -p test_preparation_safety.py -v
python -B docs/reviews/student_enrollment_final_2026-10-11/verify_b05_stage_1_12_offline.py
git diff --no-ext-diff --no-textconv --exit-code HEAD -- scripts/validation docs/reviews/student_enrollment_final_2026-10-11/SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql docs/reviews/student_enrollment_final_2026-10-11/SECURITY_CONTAINMENT_POST_B05_SUCCESSOR_DRAFT.sql supabase/migrations scripts/maintenance/reset_supabase_data.sql backend/tests/B05_RECOVERY_CONTRACT.md
git diff --check
git status --short
```

Each final command exit 0. Tests **12/12 passed**. Tracked preservation diff and
Git whitespace output empty. The verifier also checks whitespace in the changed
untracked preparation files and new report/verifier/entry artifacts, because Git
diff alone cannot check untracked edits. Final verifier output:

```text
PASS: 52/52 raw-byte pins; 40/40 migration identities/order/declared boundaries
PASS: 115/118 entry files preserved; exactly 3 allowed preparation/test/manifest changes
PASS: source/copy stops and final rollbacks; successor equality; exact ledger array
PASS: M01-M21 and OB12 register NOT RUN; unchanged runtime contract; B01-B07 OPEN
PASS: changed/new source whitespace; AST syntax only; no runtime behavior verified
WROTE: docs/reviews/student_enrollment_final_2026-10-11/B05_STAGE_1_12_OFFLINE_HASH_EVIDENCE.json
```

Exact pin-refresh command (after specification/test edits):

```powershell
@'
import hashlib,json
from pathlib import Path
p=Path('scripts/validation/b05_containment/migration_manifest.json')
m=json.loads(p.read_bytes())
changed={'scripts/validation/b05_containment/test_matrix.md','scripts/validation/b05_containment/test_preparation_safety.py'}
for row in m['pinned_inputs']:
    if row['path'] in changed:
        raw=Path(row['path']).read_bytes()
        row['sha256']=hashlib.sha256(raw).hexdigest()
        row['bytes']=len(raw)
m['targeted_oracle_revision']={'stage':'1.12','scope':['terminal_outbox_oracles','M12_cancellation_timestamp_setup','M19_wrong_tenant_actor_setup'],'execution_contract_stage':'1.10 unchanged','approval_status':'UNAPPROVED_CONSISTENCY_ONLY_INDEPENDENT_RE_REVIEW_REQUIRED'}
p.write_text(json.dumps(m,indent=4)+'\n',encoding='utf-8')
print('REHASHED: matrix and preparation test only; 40 migration identities and other pins unchanged; contract stage 1.10 retained')
'@ | python -B -
```

Exit 0; printed REHASHED line above. Historical entry capture was run before
editing and must not be rerun to replace history. Its exact command is retained
below; result exit 0, `PASS: 52/52 entry pins; recorded 118 source/package/review files before edits`.

```powershell
@'
import hashlib,json
from pathlib import Path
review=Path('docs/reviews/student_enrollment_final_2026-10-11')
package=Path('scripts/validation/b05_containment')
manifest=json.loads((package/'migration_manifest.json').read_bytes())
for row in manifest['migrations']+manifest['pinned_inputs']:
    raw=Path(row['path']).read_bytes()
    assert (hashlib.sha256(raw).hexdigest(),len(raw))==(row['sha256'],row['bytes']),row['path']
paths={r['path'] for r in json.loads((review/'B05_STAGE_1_10_ENTRY_HASHES.json').read_bytes())['files']}
paths.update(p.as_posix() for p in review.iterdir() if p.is_file())
paths.update(p.as_posix() for p in package.iterdir() if p.is_file())
paths.update(['backend/app/services/tenancy.py','backend/app/repositories/tenancy.py'])
rows=[]
for path in sorted(paths):
    raw=Path(path).read_bytes()
    rows.append({'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
output=review/'B05_STAGE_1_12_ENTRY_HASHES.json'
assert not output.exists()
output.write_text(json.dumps({'stage':'1.12 entry baseline','runtime_status':'NOT RUN','manifest_pins_match':52,'files':rows},indent=2)+'\n',encoding='utf-8')
print(f'PASS: 52/52 entry pins; recorded {len(rows)} source/package/review files before edits')
'@ | python -B -
```

Final evidence self-consistency command:

```powershell
@'
import hashlib,json
from pathlib import Path
p=Path('docs/reviews/student_enrollment_final_2026-10-11/B05_STAGE_1_12_OFFLINE_HASH_EVIDENCE.json')
e=json.loads(p.read_bytes())
for r in e['results']+e['preserved_entry_files']+e['new_review_artifact_hashes']+[e['manifest_identity']]:
    raw=Path(r['path']).read_bytes()
    assert (hashlib.sha256(raw).hexdigest(),len(raw))==(r['sha256'],r['bytes']),r['path']
assert e['runtime_cases']=={f'M{i:02}':'NOT RUN' for i in range(1,22)}
assert e['entry_changed_count']==3 and e['entry_preserved_count']==115
assert not any(line.rstrip()!=line for line in p.read_text(encoding='utf-8').splitlines())
print('PASS: final evidence/current hashes; 115 preserved/3 changed; 21 cases NOT RUN; evidence whitespace clean')
print('External evidence SHA-256: '+hashlib.sha256(p.read_bytes()).hexdigest())
'@ | python -B -
```

Exit 0; exact PASS line above plus the external evidence SHA-256. New evidence
hashes this report/verifier/entry snapshot but omits its own hash to avoid circular
self-reference. These hashes establish consistency, not independent approval.
No AGENTS.md was found in repository or checked parents. An initial source query
used a guessed Phase 7.18 filename; the actual manifest-listed filename was then
read. No verification claim relies on that failed query. Git warned about its
inaccessible global ignore file; it was neither inspected nor changed.

No SQL, migration, M01–M21, Docker command, PostgreSQL, service, worker, provider,
secret, external collection, push or deployment was executed. Runtime pins,
wrappers, derivatives, shim/supervisor/adapter/fake/observer and owner/consumer
evidence remain unavailable/unresolved. B01–B07 stay OPEN. Independent source
re-review is required; successful offline preparation does not authorize execution.
