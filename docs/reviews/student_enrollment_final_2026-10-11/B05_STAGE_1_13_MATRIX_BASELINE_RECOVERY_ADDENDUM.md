# B05 Stage 1.13 exact matrix baseline recovery addendum

2026-10-12, Asia/Calcutta.

**TARGETED RE-REVIEW PASS — B01–B07 AND EXECUTION GATES STILL OPEN**

The exact Stage 1.10 matrix was recovered from the local Git object store and
matched to its recorded raw identity. Its complete historical diff has now been
inspected. This closes the sole evidence gap that caused the original
[Stage 1.13 review](B05_STAGE_1_13_INDEPENDENT_TARGETED_RE_REVIEW.md) to fail.
That historical report and its evidence remain unchanged; this addendum
supersedes their unavailable-baseline conclusion. The three oracle fixes remain
source-consistent. The complete historical diff is now separately verified.

This is a targeted specification verdict, not execution approval. Every M01–M21
remains NOT RUN. No SQL, migration, Docker, PostgreSQL, database connection,
runtime case or provider operation was executed.

## Exact recovery

Git blob `6acc36517718cbd8b6d92d4506227b75a877b3c8` contains the baseline:

- Raw length: **84,107 bytes**.
- Raw SHA-256: `df11a19fc8f18c3b3fecfd61930657be52a06ed510c435f36b64ee05e474e4aa`.
- Recorded identity: the test_matrix.md entry in
  [Stage 1.12 entry hashes](B05_STAGE_1_12_ENTRY_HASHES.json).
- Exact bytes preserved in
  [recovered baseline](B05_STAGE_1_10_TEST_MATRIX_RECOVERED.md).

`git cat-file --batch-all-objects` examined metadata for 6,640 available objects,
including unreachable objects. Exactly one blob had the recorded 84,107-byte
length; reading and hashing that blob produced the exact recorded SHA-256.
Nothing was reconstructed from memory or inferred from a digest. No newline,
encoding or whitespace normalization was applied to the recovered file.

The current matrix remains 106,301 bytes with raw SHA-256
`a654bf895a26acd8d5f19edb2535185925c36b532c79d26ecc54e6b50324a13d`.
The [actual matrix diff](B05_STAGE_1_13_VERIFIED_MATRIX_DIFF.patch) is 26,606 bytes,
SHA-256 `7660eb87c6b08d2fa9872828b786c33f5b85c4dfbdd8b588272c9fdd7dda1572`.

## Complete diff disposition

All six unified-diff hunks were inspected, including all inserted OB12/C12/T19
text. They cover seven logical edits, with the two M12 edits sharing a hunk:

| Original location | Actual change and disposition |
| --- | --- |
| Title, line 1 | Adds Stage 1.12 targeted-oracle label; NOT RUN retained. |
| Zero-change rule, line 323 | Explicitly includes terminal queue/creation/rotation write sets and distinguishes unchanged row contents from unchanged row counts. Resolves targeted finding 1. |
| M09, line 479 | Binds I(2) cancellation to OB12-T on pending outbox suffix 2; expiry_candidates read-only contract preserved. |
| M12, lines 584–585 | Replaces incomplete cancellation wording with complete C12 state/action/timestamp and distinct retry/repair contracts. Resolves targeted finding 2. |
| M12, lines 592–593 | Binds forged-recovery exposure to the same complete direct cancellation; lifecycle/projection effects explicit; provider_started operation retention remains. |
| M19, lines 800–801 | Replaces ambiguous wrong-tenant return wording with distinct administrator-denial and authorized lookup-miss setups. Resolves targeted finding 3. |
| Before the final execution-boundary paragraph | Inserts OB12 modes/all-case register, C12 and T19. The existing final paragraph retaining legacy/consumer/runtime/B01–B07 blockers remains identical. |

All text outside these edits is preserved. The original M01–M21 case table and
all detailed NOT RUN headings are unchanged. T1/T2/T3/C/A, earlier findings and
execution boundaries remain. The new sections are the exact current sections
already reviewed against actual source in the original Stage 1.13 report.
No new unsupported schema field, clock, retry, audit or tenant-denial assumption
was found in this diff review.

The previously recovered, hash-verified
[test and manifest diff](B05_STAGE_1_13_VERIFIED_TEST_MANIFEST_DIFF.patch) remains
unchanged at SHA-256
`12949cf6d8d2ca18cde0e56c38d34ea3671c3568a6b001286f6eebbc0939425f`.
Together these patches verify all three preparation-file diffs. The original
source review and acknowledged offline test results are retained; tests were
not repeated for this artifact-only recovery.

## Separate open decisions and gates

| Decision | Still unresolved |
| --- | --- |
| B01 | Actual authentication/actor/claims/role/BYPASSRLS boundary; synthetic claim setup is not production identity proof. |
| B02 | Helpers, service defaults, direct writes and external consumers. |
| B03 | Actual creators and global/per-schema defaults, cross-schema/extension compatibility. |
| B04 | Target catalog, applied-byte provenance and target-specific manifest approval; recovered local text is not deployed-state evidence. |
| B05 | SC-06/SC-07 order, assign4 scope/self-grant exposure, create7/invite_approve7 actor trust, organization-admin compatibility and legacy rejection trust-boundary observation/disposition. |
| B06 | Consumers, maintenance/reset, audit retention/cutover, processing tokens, historical queue repair, provider uncertainty and reconciliation. |
| B07 | Exact owner approval, runtime/component identities, reviewed derivatives/wrappers, bounded execution scope and cleanup proof. |

Runtime version requirements remain requirements only. Image/digest, tools,
engine/host/interpreter/config and shim/supervisor/adapter/fake/observer/derivative
identities and availability remain unresolved. No runtime availability was
inspected. The contract remains execution_authorized=false,
runner_mode=file_only_preparation and runtime_adapter=NULL; all seven decisions
remain OPEN_OWNER_DECISION_UNRESOLVED. Stops, final ROLLBACK, validation copy and
existing runner safeguards remain unchanged. No external-consumer absence,
live database state, owner approval or execution permission is inferred.

## Bounded search and exact commands

Read-only Git commands from `F:/Git Project/CollegeAIChatbot`, PowerShell:

```powershell
git status --short
git rev-parse --git-dir
git reflog show --all --format='%H %gd'
git stash list
git log --all --format='%H' -- scripts/validation/b05_containment/test_matrix.md
git fsck --full --no-reflogs --unreachable --no-progress
```

All completed successfully. Reflogs exist; stash list and matrix path history
are empty. fsck listed unreachable objects without corruption findings. Its
large metadata output exceeded the display budget; the subsequent batch object
metadata query independently covered all available Git objects.

A repository filename scan used:

```powershell
rg --files --hidden --no-ignore -g AGENTS.md -g '*test_matrix*' -g '*.patch' -g '*.diff' -g '*.bak' -g '*.backup' -g '*.before*' -g '*Stage*1*10*' -g '*stage*1*10*' -g '!node_modules/**' -g '!.git/**' -g '!.venv/**' -g '!venv/**' -g '!backend/.venv/**' -g '!frontend/node_modules/**' -g '!.aws/**'
```

It found the current matrix, review artifacts and unrelated patch/backup names.
Two pytest-cache directories denied enumeration; no access escalation was
attempted. The exact Git blob was found before any broader backup or patch-body
search was needed. No unrelated object contents or secrets were inspected.
Git's global-ignore permission warnings did not affect the matching blob read.

The decisive object query was run via Python `-B` with captured subprocess output:

```python
proc = subprocess.run(
    ['git', 'cat-file', '--batch-all-objects',
     '--batch-check=%(objectname) %(objecttype) %(objectsize)'],
    capture_output=True, check=True)
rows = [line.split() for line in proc.stdout.decode().splitlines()]
candidates = [r[0] for r in rows if r[1] == 'blob' and int(r[2]) == 84107]
```

The sole candidate was read with
`git cat-file blob 6acc36517718cbd8b6d92d4506227b75a877b3c8` in a Python subprocess
using binary captured stdout. `hashlib.sha256(raw).hexdigest()` and `len(raw)`
matched the recorded baseline. Recovery used Path.write_bytes(raw) into the new
baseline artifact only. The patch used difflib.unified_diff with UTF-8 decoding,
splitlines(keepends=True), three context lines, and these exact filenames:
`stage1.10/scripts/validation/b05_containment/test_matrix.md` and
`stage1.12/scripts/validation/b05_containment/test_matrix.md`.

Offline final checks regenerated the patch byte-for-byte from the recovered
blob/current matrix, verified raw artifact identities and compared all 126
pre-existing relevant source/package/review files to a recovery-entry snapshot.
All 126 remain byte-identical, including the current matrix/test/manifest,
original reviews/evidence, stopped drafts/copy, authorization annex and recovered
test/manifest patch. Both baseline/current matrices retain the same 21 NOT RUN
case rows and headings; the current OB12 register remains NOT RUN. New addendum
and evidence whitespace checks pass. Unified-patch context-space markers are
intentional patch syntax.

The [recovery evidence](B05_STAGE_1_13_MATRIX_RECOVERY_EVIDENCE.json) retains the
entry identities, artifact hashes, six hunk headers, separate source/historical
diff dispositions, runtime/decision status and bounded command results. Only
four new recovery artifacts were added: baseline, matrix patch, this addendum
and recovery evidence. No existing file was edited. Recovery and review stop here.
