# Enrollment review patch v2 inspection

Reviewed 2026-10-11 against the current CollegeAIChatbot checkout using Windows
PowerShell 5.1.26100.9549 and Python 3.13.6.

**Verdict:** The four archived runners and their Python helpers reject persistent
database targets in mocked safety checks. PowerShell syntax passes. The patch
needs runtime corrections before use; live Docker/database validation remains
unverified. The active checkout still has a helper targeting the persistent DB.

## Scope and archive

- Original: `C:\Users\dsmes\Downloads\COLLEGE_AI_ENROLLMENT_REVIEW_PATCH_V2.zip`.
- Saved ZIP: `COLLEGE_AI_ENROLLMENT_REVIEW_PATCH_V2.zip` in this directory.
- SHA-256: `FAE25FAB07A20F6156DE9CEC20F912A7621DF3521761342FCEB5652E26FC3FCF`.
- All 14 extracted files under `source/` match their ZIP entries byte for byte.
- Relative to this checkout: seven replacements and seven additions; see
  `inventory.json` and `patch_vs_checkout.diff`.
- The archive contains proposed enrollment documentation, six Python files, and
  four PowerShell runners. It contains no executable enrollment migration.
- Document instructions, including extracting into the repository root and
  rehearsing migrations, were reviewed as document content. This inspection did
  not apply the patch, approve product policies, or execute its database suites.

## Verification results

| Archived runner | PowerShell parsing | Persistent name rejected | Persistent full ID with volume rejected | All rejection scenarios |
| --- | --- | --- | --- | --- |
| `verify_academic_setup_database.ps1` | PASS | PASS | PASS | 8/8 |
| `verify_faculty_assignment_database.ps1` | PASS | PASS | PASS | 8/8 |
| `verify_faculty_attendance_database.ps1` | PASS | PASS | PASS | 8/8 |
| `verify_faculty_tests_database.ps1` | PASS | PASS | PASS | 8/8 |

Each PowerShell script was invoked with mocked Docker and Python entry points.
The persistent-ID scenario executes its actual inline Python guard against
mocked inspection data containing a named volume, even with matching validation
labels. Rejection occurs before `docker cp`, `psql`, or stopping an unowned
target. The other scenarios cover the persistent name, validator nonzero exit,
empty validator output, unavailable Python command, DOCKER_HOST override,
nonlocal context, and unexpected engine. Readiness probes (`pg_isready` and
reading `/proc/1/comm`) precede validation; they are not SQL fixture execution.

Additional checks:

- All six archived Python files compile without syntax errors.
- All six bundled unit tests pass.
- All four concurrency CLI helpers reject both
  `supabase_db_CollegeAIChatbot` and a full-ID fixture with persistent storage
  before SQL, database subprocesses, or fixture reads.
- Nine extra guard rejection cases pass: wrong ID, stopped container, wrong
  image, missing labels, wrong purpose, bind mount, extra mount, missing
  auto-removal, and missing tmpfs configuration.
- Two additional tests reproduce the tmpfs compatibility/size findings below.
  These tests passing means the finding was reproduced, not that the behavior
  is correct.
- Saved evidence: `powershell_parse.json`, `runner_results.json`, and
  `native_arguments.json`.

## Findings requiring attention

1. **High: the active faculty-assignment helper targets the persistent database.**
   The repository's `scripts/validation/faculty_assignment_concurrency.py:7`
   sets `CONTAINER = "supabase_db_CollegeAIChatbot"`. Its `main()` explicitly
   accepts the project's Supabase container and host port 54322, then runs
   fixtures/concurrency mutations. The archived replacement removes that target
   and uses the shared guard. Archiving alone does not change the active helper.

2. **High: tmpfs creation and validation expect different metadata layouts.**
   All archived runners create storage with `--tmpfs` at line 17, while
   `disposable_container.py:62` requires a tmpfs object in `Mounts` and line 64
   also requires `HostConfig.Tmpfs`. In the inspected Moby v28.5.2 implementation,
   legacy `HostConfig.Tmpfs` mounts are handled separately from `MountPoints`,
   and inspect's `Mounts` is generated from `MountPoints`. From that source, the
   inferred result is that the current `--tmpfs` path produces a container the
   guard rejects. A fixture with `Mounts=[]` and the correct bounded
   `HostConfig.Tmpfs` reproduces rejection. This was not verified against the
   installed engine because it is unavailable. Correct creation and validation
   together; simply changing to `--mount` would also require revising the guard's
   mandatory `HostConfig.Tmpfs` check. See
   [Moby tmpfs and mount inspection implementation](https://github.com/moby/moby/blob/v28.5.2/container/container_unix.go#L370)
   and [inspection response construction](https://github.com/moby/moby/blob/v28.5.2/daemon/inspect.go#L43).

3. **High: cleanup label lookup loses quotes under Windows PowerShell 5.1.**
   All archived `finally` blocks use native Docker arguments containing
   `{{ index .Config.Labels "collegeai.validation.run" }}`. The native argument
   recorder confirms that PowerShell passes
   `{{ index .Config.Labels collegeai.validation.run }}` instead. That is not the
   intended Go-template string lookup. Cleanup can fail before stopping the
   owned container; `--rm` only removes it after it stops. Prefer plain
   `docker inspect $containerId`, check its exit code, deserialize JSON, and
   compare the label with the run token. Keep refusal of unowned targets.

4. **Medium: relative fixture paths depend on the caller's working directory.**
   Attendance and assessment helpers read
   `Path('scripts/validation/..._database.sql')`. The archived attendance/tests
   runners removed the previous `Push-Location $repository` behavior and do not
   replace it. Calling them from another directory therefore fails after
   migration replay. Resolve fixture paths from `__file__`, or establish and
   restore the repository working directory around helper invocations.

5. **Medium: the guard does not enforce bounded tmpfs options.**
   Its check validates the destination keys but never examines the options
   value. An otherwise accepted fixture with `Tmpfs={...: "rw"}` still passes.
   Runners request `size=536870912`, but the shared validator's documented
   bounded-storage guarantee is stronger than its implementation. Validate
   an explicit positive size within the intended limit.

## Runtime limits

A read-only Docker preflight was attempted. The restricted process could not
read Docker configuration; a permitted read-only retry reached the client but
found no Docker Desktop Linux engine named pipe. No container metadata was
captured. No real container was created, copied into, stopped, or connected to,
and no SQL, fixture, migration, or remote database operation was executed.

The mocked checks establish rejection behavior and native argument recording
establishes the PowerShell quoting issue. They do not establish image bootstrap,
real container mount layout, migration success, or real cleanup success.

## Reproducing the review

From the repository root:

```powershell
$review = 'docs\evidence\patch_reviews\college_ai_enrollment_review_patch_v2'
& '.\.venv\Scripts\python.exe' -m unittest discover -s "$review\source\scripts\validation" -p 'test_disposable_container.py' -v
& '.\.venv\Scripts\python.exe' "$review\review_safety.py"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$review\native_arguments.ps1" -Python (Resolve-Path '.\.venv\Scripts\python.exe').Path
& '.\.venv\Scripts\python.exe' "$review\archive_inventory.py"
```

The review harness shadows all Docker operations and never invokes real Docker.
It invokes each archived runner in a child PowerShell process to preserve its
exit status. These commands inspect the archived patch rather than apply it.
