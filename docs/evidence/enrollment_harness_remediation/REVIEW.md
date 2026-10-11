# Enrollment validation harness remediation

Completed in the active checkout on 2026-10-11. This repairs the validation
harness reviewed in archived patch v2. It does not implement the proposed
enrollment schema.

**Result:** The four PowerShell database verifiers, all four concurrency helpers,
and the Python data-reset verifier now use validated disposable container IDs.
Cleanup quoting, bounded tmpfs validation, and fixture paths are repaired.
All 27 Python safety tests and all 92 mocked PowerShell scenarios pass, including
the original 32 scenarios. No live database validation was performed.

## Changed active files

All paths below are relative to `scripts/validation/`.

| File | Change | Result |
| --- | --- | --- |
| `disposable_container.py` | Added | Shared local-engine, target, storage, and cleanup ownership validation; command-line interface for PowerShell. |
| `verify_academic_setup_database.ps1` | Modified | New isolated container, validation before readiness, exact-ID commands, guarded cleanup. |
| `verify_faculty_assignment_database.ps1` | Added | Disposable runner replacing the need to invoke assignment races against the project database. |
| `verify_faculty_attendance_database.ps1` | Modified | Same ownership/isolation rules; absolute helper paths. |
| `verify_faculty_tests_database.ps1` | Modified | Same rules; passes the same ID/token/purpose to attendance and assessment helpers. |
| `academic_setup_concurrency.py` | Modified | Safe to import; CLI validation precedes fixtures; unconfigured SQL calls fail. |
| `faculty_assignment_concurrency.py` | Modified | Removes the persistent project target/54322 acceptance; requires full ID/token/purpose. |
| `faculty_attendance_concurrency.py` | Modified | Removes the fixed container name; validates configuration and resolves its fixture from `__file__`. |
| `faculty_tests_concurrency.py` | Modified | Configures the imported attendance helper and uses its current validated ID for lock-holder processes; resolves its fixture from `__file__`. |
| `verify_supabase_data_reset.py` | Modified | Applies the same isolation, validation-before-readiness, and ownership cleanup to this additional database verifier. |
| `test_disposable_container.py` | Added | 27 guard, helper, fixture-path, import-safety, and reset-runner regressions. |
| `test_runner_safety.py` | Added | Original 32 rejection scenarios plus 60 runtime regressions; real guard code with mocked subprocesses. |
| `test_runner_worker.ps1` | Added | Shadows all external command entry points during PowerShell tests; never invokes Docker or SQL. |

There are eight modified and five added active files. The original eight files
were checked against Git HEAD before replacement and saved byte for byte under
`baseline/`; `baseline.json` records their original hashes. No reset, stash,
checkout, commit, or changes outside the harness were used to prepare the repair.
The archived ZIP and all 14 extracted source files remain unchanged.

## Target and cleanup rules

- Docker commands pin `--context desktop-linux`. Preflight rejects a DOCKER_HOST
  override or a different DOCKER_CONTEXT, inspects the context's local Linux
  named-pipe endpoint before contacting an engine, and requires
  `docker-desktop linux`. No remote context or Supabase endpoint is accepted.
- Containers are newly created with `--pull=never --rm --network none`, a fresh
  full run-token label, a purpose label, a matching generated name, and the
  expected PostgreSQL image. They publish no ports.
- Data storage uses `--tmpfs /var/lib/postgresql/data:rw,size=536870912` with an
  explicit matching PGDATA. Validation accepts legacy `HostConfig.Tmpfs` with
  `Mounts=[]` or one mirrored tmpfs entry. It rejects persistent/bind/extra or
  inherited mounts, absent/invalid/duplicate size options, nonpositive sizes,
  limits above 512 MiB, and missing/conflicting PGDATA values.
- Before readiness or fixture execution, inspection must return the supplied
  full 64-character ID with the exact run name, token, purpose, image, disposable
  label, and auto-removal setting. Runners also compare the guard's returned ID
  to the creation result. Names, shortened IDs, alternate returned IDs, and
  persistent project containers fail; there is no fallback target.
- SQL helpers start unconfigured. Failed reconfiguration or CLI parsing clears
  prior configuration. Assessment SQL uses the imported attendance helper's
  configured target; its subprocesses reference that current ID rather than an
  imported stale value. Every helper's Docker execution pins the context.
- Cleanup runs only after this invocation's successful creation returned a full
  ID. It performs fresh **plain JSON inspection**, checks exact ID/name/token/
  purpose/image/disposable marker/auto-removal, then stops only that ID using a
  ten-second timeout. `--rm` handles removal. There are no name-based removals,
  bulk/prune operations, or volume deletion commands.
- Ownership authorizes cleanup even when the run-owned container fails storage
  validation or bootstrap. Failure to inspect or establish ownership refuses
  cleanup. PowerShell cleanup failure makes the overall exit status nonzero.

## Actual verification

Environment: Windows PowerShell **5.1.26100.9549**, Python **3.13.6** from the
repository's `.venv`. All subprocesses that could run Docker/database commands
in these tests were replaced with command doubles.

| Check | Actual result | Evidence |
| --- | --- | --- |
| Python guard/helper/reset unit suite | **27/27 PASS**, exit 0 | `python_safety_results.txt` |
| Original PowerShell safety cases | **32/32 PASS** | `runner_results.json` |
| Additional PowerShell regression cases | **60/60 PASS** | `runner_results.json` |
| Academic runner | **23/23 mocked scenarios PASS** | `runner_results.json` |
| Assignment runner | **23/23 mocked scenarios PASS** | `runner_results.json` |
| Attendance runner | **23/23 mocked scenarios PASS** | `runner_results.json` |
| Assessment runner | **23/23 mocked scenarios PASS** | `runner_results.json` |
| PowerShell parsing | **8/8 files PASS**, including all four database runners and the test worker | `powershell_parse.json` |
| Python syntax parsing | **9/9 validation Python files PASS** | Source inspection and `source_manifest.json` |
| Persistent-target/default-connection audit | **No matches in the ten production harness files** | `verification_summary.json`, `verify_evidence.py` |
| Git whitespace check | **PASS** | `git diff --check`, exit 0 |
| Original archive integrity | **PASS**, all extracted entries unchanged | `verification_summary.json` |
| Docker availability | Linux named pipe absent; no Desktop/backend process observed | `docker_availability.json` |
| Live containers, migrations, SQL, database connections | **NOT RUN** | Strict task boundary and unavailable engine |

The 92 PowerShell cases include valid isolated command routing from a working
directory outside the checkout; persistent name/full-ID rejection; validator
failure, empty/mismatched output, and unavailable command; creation failure;
unbounded tmpfs; owned storage failure; copy failure; wrong cleanup token/name;
invalid/failed cleanup inspection; empty/mismatched cleanup output; stop failure;
and remote host/context/endpoint refusal. Positive cases invoke only command
doubles: a recorded `psql` or migration filename in the trace is not SQL execution.

The initial runner test assertion treated the numeric timeout argument recorded
by a PowerShell function as a string. The recorder was corrected to model native
argument strings; the final rerun passed all 92 cases with exit 0. Detailed final
traces, including expected rejection stderr, are saved in `runner_results.json`.

Commands executed from the repository root:

```powershell
& '.\.venv\Scripts\python.exe' -m unittest discover -s scripts/validation -p test_disposable_container.py -v
& '.\.venv\Scripts\python.exe' 'scripts\validation\test_disposable_container.py'
$env:COLLEGEAI_HARNESS_EVIDENCE = (Join-Path (Get-Location).Path 'docs\evidence\enrollment_harness_remediation')
& '.\.venv\Scripts\python.exe' 'scripts\validation\test_runner_safety.py'
git diff --check
& '.\.venv\Scripts\python.exe' 'docs\evidence\enrollment_harness_remediation\verify_evidence.py'
```

PowerShell files were parsed using the following API; the recorded run also
collected file names, PowerShell version, and error lists in `powershell_parse.json`:

```powershell
Get-ChildItem -LiteralPath 'scripts\validation' -Filter '*.ps1' | ForEach-Object {
    $tokens = $null
    $errors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile(
        $_.FullName, [ref]$tokens, [ref]$errors)
    if ($errors.Count) { throw ($errors | Out-String) }
}
```

Python syntax was inspected with `ast.parse` for each `.py` in
`scripts/validation/`; `verify_evidence.py` also parses each changed Python file.
No database runner was invoked directly against real commands.

## Persistent-target audit and scope

The four concurrency helpers, four PowerShell database verifiers, shared guard,
and data-reset verifier contain no persistent project container name, port
54322, database URL, or direct database-client fallback. Persistent target strings
remaining in tests are rejection fixtures; those in the archive/baseline are
preserved review history. All lock-holder subprocesses in the active helpers
use `docker_arguments` and the already configured full ID.

Three existing tools under `scripts/validation/` are intentionally local-stack
administration tools rather than disposable verification runners:
`invoke_local_supabase.ps1`, `manage_local_super_admin.ps1`, and
`provision_local_demo_users.ps1`. They invoke explicitly selected local actions,
with reset confirmation or administrative inputs/password as applicable, and
report their local target. They were inspected and parsed but were not executed
or changed. No broad claim that these administration tools reject the persistent
stack is made.

## Remaining limitations

Docker remains unavailable. Real image bootstrap, actual installed-engine
inspection metadata, migration replay, SQL/concurrency contracts, and container
auto-removal have not been validated. The guard is deliberately specific to the
local Windows Docker Desktop Linux context/pipe and this image; other Docker
configurations fail closed. The image must already be cached because runners
use `--pull=never`.

Ruff is not installed in the repository's `.venv`; the attempted availability
check failed. No Ruff lint pass is claimed. Parsing, regression tests, source
inspection, and the Git whitespace check provide the verification listed above.

No SQL/migration files, enrollment DDL, application/frontend code, or proposed
enrollment policy documentation were applied or changed. No database connection,
database mutation, remote Supabase contact, or real container operation occurred.
Live database validation requires a separate authorized step after Docker is
available.

`remediation.diff` contains the complete change against the saved baseline,
including additions. `source_manifest.json` records SHA-256 hashes for all 13
changed active files; `verification_summary.json` records the verification totals.
