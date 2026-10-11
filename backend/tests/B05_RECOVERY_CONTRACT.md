# B05 local recovery contract

This is an implementation contract, not deployment approval. Acceptance uses the
user's P1-P7 checklist and the available B05 routine review/remediation design.
No separate Stage 1.1 independent implementation report was discoverable in this
working tree. PostgreSQL/provider behavior is NOT RUN; mocks establish Python
orchestration only.

| Interruption boundary | Durable state / next attempt |
| --- | --- |
| Before reservation commits | No operation; retry reservation |
| Reservation commits, response lost | Resolve original operation by invitation/digest |
| Before provider-start CAS commits | Reserved; retry CAS |
| Provider-start commits, response lost or process stops before provider call | Provider-started; freeze (cannot prove the call did not start) |
| Provider call fails, times out, or returns before its ID is recorded | Provider-started; freeze; require correlated provider evidence |
| Provider-ID write commits, response lost | Provider-created; resume without creating Auth account |
| Before public-user provisioning commits | Provider-created; retry provisioning RPC |
| Public-user insert and operation update commit, response lost | User-created; resolve recorded user; no second insert |
| Before grant/acceptance/audit transaction commits | User-created; retry finalization |
| Finalization commits, response lost | Accepted; retry returns original result, then confirms email |
| Confirmation fails or its response is lost | Accepted; repeat email-confirmation only (never password) |
| Before confirmation-state write commits | Accepted; repeat confirmation and write |
| Confirmation-state write commits, response lost | Confirmed; return result without provider I/O |
| Expiry before finalization | Freeze; no role or acceptance success; retain operation and account |

`test_each_interruption_boundary_recovers_or_freezes` injects failures on both
sides of durable writes. The HTTP retry test uses the real token resolver.
Existing-account acceptance requires the canonical verified user/Auth ID and
email, and never sends or updates a password. Issuer/recipient/tenant checks for
new grants remain in finalization. SQL locks invitation before operation;
rotation/cancellation/expiry hold the invitation row too. Only an unstarted new
account reservation may be closed by guarded recovery. IDs are never cleared.
Uncertain or completed provider work cannot be cancelled successfully. Both
invitation kinds permit explicit closure only of an unstarted new-account
reservation; neither automatically releases reservations.
Stage 1.4 adds password-free `/recover` endpoints for both invitation kinds.
Database recovery binds the presented generation to the accepted operation,
new-account flag, accepted user and recorded Auth ID plus active canonical user.
Frontend reload and post-timeout inspection expose confirmation recovery without
sign-in. Existing-account membership still requires its verified principal.
Unknown provider outcomes require an owner-approved evidence/recovery command;
none that guesses failure or deletes identities is exposed here.

Membership decisions and their `membership:<request_id>` audit keys use one SQL
transaction. Repeated decisions reach the RPC and repair a missing correlated
audit before returning success. Provider confirmation follows that transaction
and can be retried. Student approval uses a separate command: verified, active,
institution-scoped admin/staff, active tenant, stored student/account linkage,
configured student role. Approval, scoped grant and `student:<student_id>` audit
commit together; existing approved profiles are repairable. Invitation role
allowlists remain admin/staff/faculty. Offline failures exercise service/RPC
boundaries; audit INSERT rollback and database uniqueness still need engine tests.

The changed assertions now require the durable RPC result and its actor/tenant/
recipient arguments. Positive finalization, real HTTP retry and student RPC tests
replace the former standalone writer assumptions. SQL-string tests are source
checks, not proof of transactions or PostgreSQL concurrency.

Legacy compatibility is **BLOCKED**. Discoverable production edges are
`platform_institutions.assign_institution_admin` -> platform role repository ->
five-argument assignment; tenancy role wrappers -> that same overload; legacy
`tenancy.decide_membership_request` -> new atomic legacy decision RPC -> existing
five-argument assignment check. Stage 1.4 fixes stored approved/rejected values,
decision/grant/audit partial writes and identical actor/reason retries. Rejection
preserves all existing grants; the retained cleanup callable performs no deletion.
No current API edge to the latter was found. Its documented organization/admin
allowance in `docs/status/PHASE_6_13_1_SCOPE_REPORT.md` differs from the guarded SQL
contract. Organization-admin approval disposition remains unresolved; denial in
the assignment check now rolls back the decision rather than leaving it approved.
The legacy seven-argument `phase723_approve_membership_with_invitation` calls the
seven-argument outbox-create overload. Its invitation-on-approval contract remains
documented in `PHASE_7_23_STAFF_FACULTY_ONBOARDING_ROSTER.md`; current membership API
uses immediate approval/grant. Searches covered backend, scripts, migrations,
tests and docs. No source caller is not proof of no external consumer.

Minimum owner decision: inventory external callers for both legacy approval and
four-argument assignment, then accept authenticated actor mapping and guarded
retention or retirement, plus the organization-admin legacy service disposition.
This patch removes Stage 1's proposed unconditional failure replacement of the
four-argument identity; it neither drops nor revokes these legacy routines. Their
authorization gaps remain hard blockers, including F04 and the old self-assignment
path. They must not be described as fixed by the new overload.

Migration source: only the user-identified unexecuted B05 file moves from duplicate
`20261011000000` to next source-chain version `20261017000000`; historical migrations
are unchanged. Source declares postgres defaults granting new functions to
anon/authenticated/service_role. New functions explicitly deny client EXECUTE;
private helpers also deny service EXECUTE; operation-table writes are private.
Existing replacements retain signature/ACL history; six/seven create overloads and
four/five assignment overloads remain distinct. New object owners depend on the
runner; deployed ownership, effective inherited/column ACLs and ledger are
**UNVERIFIED**. Repository replay scripts use `psql -f` without `-1`; the new source
has explicit BEGIN/COMMIT to avoid publishing intermediate default grants.
Actual runner wrapping/claims, complete definitions, rollback, grant/audit failure
injection, expiry races, cancellation/finalization/rotation interleavings and
full-chain compatibility require separately authorized runtime validation.
Cancellation/expiry now use a transactionally written immutable lifecycle audit
for both invitation kinds; institution-admin projection commits alongside it.
Terminal retries repair missing events without repeating decisions. Expiry
candidate collection includes old expired rows missing their lifecycle event.
Issuer attribution for expiry, repair actors and unknown initiators on direct
cancellation are explicit, never inferred human approval records. Historical
terminal repair writes the authoritative event with a repair flag; it does not
guess whether an old uncorrelated institution projection is missing. SQL source
checks and transaction fakes do not prove PostgreSQL rollback or trigger behavior.

The original containment candidate requires exactly 11 audit columns. The separate
`SECURITY_CONTAINMENT_POST_B05_SUCCESSOR_DRAFT.sql` requires the exact 12-column
post-B05 layout, unique decision-key index and exact 40-version source chain;
both original stops and ROLLBACK remain. Choose independently approved pre-B05
sequencing or review this successor
after B05; no candidate is assumed applied. New B05 owner/ACL/trigger objects also
need catalog review. Neither migration nor successor is certified safe to deploy.

Stage 1.4 changed files (relative to the working tree at task start):

- `backend/app/api/`: `admin_invitations.py`, `super_admin_registration.py`.
- `backend/app/repositories/`: `platform_admin_invitations.py`, `tenancy.py`.
- `backend/app/schemas/`: `admin_invitations.py`, `super_admin_registration.py`.
- `backend/app/services/`: `invitation_operations.py`, `platform_admin_invitations.py`, `student_registration.py`, `super_admin_registration.py`, `tenancy.py`.
- `backend/tests/`: this contract, `run_b05_offline.py`, `test_b05_invitation_acceptance_security.py`, `test_b05_stage14_source_fixes.py`, `test_organization_institution_phase_6_13_1.py`, `test_phase_7_14_super_admin_university_admin_lifecycle.py`, `test_phase_7_15_invitation_delivery_email_verification.py`, `test_phase_9_super_admin_registration.py`, `test_role_scope_enforcement_phase_6_13_7.py`.
- `frontend/src/`: `features/adminInvitation/AdminInvitationPage.tsx` and its test, `features/superAdmin/SuperAdminRegistrationPage.tsx` and its test, `services/adminInvitationApi.ts` and its test, `services/superAdminInvitationApi.ts`, `types/platform.ts`, `test/b05Offline.ts`; also `frontend/vitest.b05-offline.config.ts`.
- SQL: `supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql`, `docs/reviews/student_enrollment_final_2026-10-11/SECURITY_CONTAINMENT_POST_B05_SUCCESSOR_DRAFT.sql`.
