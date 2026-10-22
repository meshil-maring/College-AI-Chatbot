# Audit verification and remaining evidence

Reviewed: 2026-10-21 (Asia/Calcutta). Local source checks and database-double
tests are distinct from live catalog/data/concurrency validation.

## Checks performed

| Check | Result | Evidence |
| --- | --- | --- |
| Academic setup, class registration, subject assignment, faculty responsibility, and frontend RBAC tests | 256 passed; one existing TestClient deprecation warning. Database doubles only. | `logs/backend/curriculum-audit-focused-tests-retry.log` |
| Frontend RBAC source snapshot | Matches backend catalogue; does not enumerate live grants. | `logs/backend/curriculum-audit-rbac-snapshot.log` |
| Backend source structure | Checked after documentation completion. | `logs/backend/curriculum-audit-structure.log` |
| Frontend source structure | Checked after documentation completion. | `logs/frontend/curriculum-audit-structure.log` |
| Documentation links, source anchors and maintenance limits | Checked after final review. | `logs/backend/curriculum-audit-documentation.log` |
| Inspected-source fingerprints | Local paths, SHA-256 and migration order; excludes private configuration. | `logs/backend/curriculum-audit-source-inventory.json` |

Logs are repository-local output outside application source roots, not proof of
deployed state. Fingerprints identify reviewed bytes, including relevant
uncommitted workspace changes.

The first test attempt could not collect because the inherited DEBUG setting
was not a valid boolean. The passing retry used process-local `DEBUG=false` and
`ENVIRONMENT=testing`, disabled bytecode writes and pytest's unwritable cache,
and changed no configuration file:

```powershell
cd backend
$env:DEBUG='false'
$env:ENVIRONMENT='testing'
$env:PYTHONDONTWRITEBYTECODE='1'
.venv/Scripts/python.exe -m pytest -p no:cacheprovider `
  tests/test_academic_setup.py tests/student_subjects `
  tests/test_student_class_registrations.py `
  tests/test_faculty_responsibilities.py tests/test_frontend_rbac_policy.py -q
python scripts/generate_frontend_rbac.py --check
```

Passing tests cover existing validation/role/scope paths, not all findings.
They do not reproduce a real deletion race, audit failure after commit,
effective RLS/grants, or future package behavior.

## Evidence not collected

- Current migration ledger, catalog definitions, routine bodies/owners, effective
  grants, RLS policies, bypass roles, or default privileges.
- Existing duplicate/inconsistent student, class, subject, roster, or identity rows.
- Real concurrent deletion, assignment/audit failure, capacity, revocation,
  deadline, and retry behavior.
- Runtime credentials, private configuration audit, or remote exposure.

Historical deployment reports do not replace current catalog/data evidence.
The exported schema snapshot and archived SQL drafts are not the final applied
schema by assumption.

## Live read-only catalog and aggregate data review

Use an authorized read-only connection and consistent snapshot. Bound query load.
Collect definitions and aggregate counts, avoiding student names, addresses,
emails, raw identifiers, and credentials. Do not run DDL, migrations, fixture
inserts, cleanup, schema repairs, or application mutation routines.

| Review | Required result |
| --- | --- |
| Migration ledger versus source | Identify unapplied, divergent or manually modified relevant objects. |
| Columns/types/nullability/defaults | Establish actual legacy curriculum semester columns and registration/batch shapes. |
| Keys and constraints | Verify PK/unique/FK/CHECK scope, delete actions, deferrability, validation state and indexes. |
| Triggers/routines | Verify actual guards, audit behavior, owners, security mode and search path. |
| Effective privileges | Inspect table/sequence/function rights for PUBLIC, anon, authenticated and service roles, including inherited/default grants and TRUNCATE. |
| Row security | Check enabled/forced state, policies, ownership and bypass capabilities. |
| Academic codes | Count exact and normalized duplicates; distinguish legitimate same codes in different owners. |
| Ancestry | Count orphaned, wrong-tenant/program/year/term and inconsistent batch/context references. |
| Class identity | Count ambiguous section-code groups and mixed cohorts; identify intentional combined teaching. |
| Identity/snapshots | Count conflicting register/roll bindings and canonical/snapshot differences without disclosing individual values. |
| Subject memberships | Count duplicate linked students within one section, conflicting identifiers and unexplained registration-to-roster relationships. |
| Curriculum applicability | Inventory reusable/dated links, legacy numbers, repeated subjects/stages and cross-department subjects. |
| History/capacity | Count lifecycle ambiguities and capacity exceptions; do not repair them during collection. |

Checks needing a new interpretation, such as normalized institutional identifiers,
must use an approved rule. A nonzero count needs triage; it does not authorize
deduplication, deletion, reassociation or identity repair.

## Disposable runtime checks before enablement

Existing database-verification helpers replay migrations and create fixtures;
they are not read-only live auditors. None was executed here. Follow their
safety requirements in a disposable environment when validation is undertaken.

Required cases:

1. Reproduce SEC-01 with concurrent attendance insertion/deletion; prove history
   survives the proposed correction.
2. Compare manual/import/assignment eligibility for wrong program/year,
   cross-tenant, and conflicting-identity cases.
3. Inject audit failure; prove no partial assignment, decision or membership
   commits, including retries after a previous failure.
4. Validate class/placement/curriculum mappings against legacy shapes, keeping
   ambiguous groups unresolved and old identifiers intact.
5. Test full-package rollback, common-core reuse, capacity races, concurrent
   first selections/approvals and one-active-assignment uniqueness.
6. Revoke permissions/responsibilities while operations wait; recheck authority
   after locks before committing changes.
7. Test before/at/after cutoff, queued work, timezone/date conversion, stale
   requests and policy/package-content edits.
8. Test subject end/rejoin, reconciliation, imports, marking eligibility, exam
   completeness, history and student/report projections.
9. Test browser table/RPC denial and allowed actors under the final scoped
   permission design.
10. Test privileged audit TRUNCATE restrictions and append-only behavior using
    disposable data and approved privilege boundaries.

The [proposal acceptance plan](../implementation-plan.md#acceptance-and-verification-plan)
still applies; these cases add coverage for the audit findings.

## Exit criteria

Source review is complete with reproducible references and reflected design
gaps. Implementation readiness also needs settled relationships/policies and a
plan for current defects. Release readiness requires catalog/data review,
disposable runtime checks and affected regressions; it cannot be inferred from
these documents or the 256 database-double tests alone.
