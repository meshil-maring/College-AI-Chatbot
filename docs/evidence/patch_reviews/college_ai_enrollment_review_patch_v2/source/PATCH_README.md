# College AI Chatbot — Enrollment Design and Validation Harness Patch

This is a review patch for the existing `CollegeAIChatbot` repository. Extract the ZIP **into the repository root** so the paths below merge with existing `scripts/validation` and `docs` folders.

## Contents

- Proposed ADR for stable student identity, enrollment episodes, placement history, identifiers, and event history.
- Revised schema design proposal (documentation only; no executable enrollment DDL).
- Validation plan v2.
- Shared disposable-container target validator.
- Refactored concurrency helpers and isolated runners for academic setup, faculty attendance, faculty tests, and faculty assignments.
- Six unit tests for the shared container-target validator.

## Validation performed here

- Python syntax compilation passed for all six Python files.
- Six mocked unit tests passed for valid isolated target acceptance and rejection of wrong tokens, persistent volumes, published ports, network access, and arbitrary target names.
- No PowerShell runtime was available, so `.ps1` files were not executed or runtime-parsed.
- No Docker commands, SQL, migrations, database connections, or remote Supabase operations were run.

## Safety properties

Each runner is designed to create a unique, auto-removed container using the expected Supabase PostgreSQL image, a bounded tmpfs data directory, no host ports, and `--network none`. Helpers require the exact full container ID, run token, and purpose label before issuing SQL. Cleanup checks the run token before stopping the exact created container.

## Before applying

1. Review the patch diff.
2. Keep a clean Git checkpoint.
3. Confirm PowerShell parsing on the target Windows machine.
4. Review the proposed ADR; policy decisions are recommendations, not yet approved.
5. Do not add or execute enrollment DDL until the exact draft is recovered, security evidence is reconciled, and separate disposable SQL execution is authorized.
