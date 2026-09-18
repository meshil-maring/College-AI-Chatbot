# PHASE 6.13.4 — Organization & Institution Approval Workflow

## 1. Files Changed

### New Files
- `backend/app/api/organizations.py` — approval endpoint wiring
- `backend/app/api/institutions.py` — join-request decision endpoint wiring
- `backend/tests/test_approval_workflow_phase_6_13_4.py` — 22 focused security tests

### Modified Existing Files (reused, not rewritten)
- `backend/app/services/tenancy.py` — `decide_organization` service function added
- `backend/app/repositories/tenancy.py` — `update_join_requests_for_organization` cascade helper
- `backend/app/services/authorization.py` — `assert_can_manage_organization` restored to Phase 6.13.1; approval gate moved to `_assert_platform_authority`
- `backend/app/main.py` — regressed lines restored during test-driven fix

## 2. Migration Created

**None.** No new migration was required. The approval workflow reuses the schema introduced in Phase 6.13.1:

- `organizations.status` — `pending | active | suspended | rejected`
- `institution_join_requests.status` — `pending | approved | rejected`
- `institutions.status` — `pending | active | suspended | rejected`
- `trg_phase613_institutions_status` — derives `is_active` from `status`

No schema change was needed.

## 3. Approval Endpoints

Both endpoints are thin API layers that delegate to the existing service layer. They are **not public**: they require a valid JWT (enforced by `get_current_user` dependency).

### POST `/api/v1/organizations/{organization_id}/decision`
- Body: `{"decision": "approve"}` or `{"decision": "reject"}` (optional `reason`)
- Authorization context resolved server-side from JWT → calls `decide_organization`
- Response: `DecisionResponse(decision, message)`

### POST `/api/v1/join-requests/{join_request_id}/decision`
- Body: `{"decision": "approve"}` or `{"decision": "reject"}` (optional `reason`)
- Authorization context resolved server-side from JWT → calls `decide_join_request`
- Response: `DecisionResponse(decision, message)`

No new schemas introduced. Both reuse existing `ApprovalDecisionRequest` / `DecisionResponse` pydantic models.

## 4. Organization Approval Behavior

| Requirement | Implementation |
|---|---|
| Pending organizations cannot access protected tenant resources | Inherits from 6.13.1-6.13.3 scope model — `status != active` blocks scoped operations |
| Only platform-level authority can approve/reject | `_assert_platform_authority` rejects org-scoped and institution-scoped admins |
| Approval → correct active state | `update_organization_status(db, org_id, 'active')` |
| Rejection → inaccessible | `update_organization_status(db, org_id, 'rejected')` |
| Repeated decisions handled safely | Conditional guard returns 422 `ORGANIZATION_NOT_PENDING` |
| Org admin cannot self-approve | `_assert_platform_authority` rejects `scope_type == ORGANIZATION` |

## 5. Institution Approval Behavior

| Requirement | Implementation |
|---|---|
| Pending join request cannot activate institution | `decide_join_request` requires `request.status == pending` |
| Only authorized org-level admin can decide | `assert_can_decide_join_request` checks `scope_type == ORGANIZATION` + org match |
| Approval activates institution | `update_join_request_status` → `approved`; `update_institution_status_for_join` → `active` |
| Rejection leaves inactive/rejected | `update_institution_status_for_join` → `rejected` |
| Repeated decisions safe | Conditional update (`.eq("status", "pending")`) returns None → 409 |
| Institution cannot approve itself | Requires org scope, not institution scope |
| Org A cannot approve Org B's request | `assert_can_decide_join_request` verifies `request.organization_id == authz_context.organization_id` |
| Tenant isolation server-side | All scope resolution reads `user_roles` by `user_id` from JWT |

## 6. Role/Scope Behavior

- **No new roles**. Existing vocabulary (`admin`, `faculty`, etc.) reused.
- **No `institution_admin` role**. Institution admins use `role='admin' + scope_type='institution' + scope_id=institution.id` (established in Phase 6.13.3).
- After approval, the initial admin already has correct institution scope (granted during registration). Approval workflow does not reassign or widen scopes.
- Organization admin scope grants management of all institutions under that org but does **not** grant platform-wide authority or the ability to approve/reject the organization itself.
- Institution admins receive **only** institution scope — cannot access another institution, cannot manage the parent organization.

## 8. Tests Run

| Suite | File | Tests | Result |
|---|---|---|---|
| Phase 6.13.4 approval workflow (16 areas) | `backend/tests/test_approval_workflow_phase_6_13_4.py` | 22 | 22 passed |
| Phase 6.13.1 regression | `backend/tests/test_organization_institution_phase_6_13_1.py` | 31 | 31 passed |
| Phase 6.13.2 regression | `backend/tests/test_organization_registration_phase_6_13_2.py` | 19 | 19 passed |
| Phase 6.13.3 regression | `backend/tests/test_institution_registration_phase_6_13_3.py` | 76 | 76 passed |

**Total: 148 passed, 4 skipped, 0 failures.**

### 16 Security-Test Areas Covered

1. Authorized organization approval (platform admin approves → `active` + cascade)
2. Unauthorized organization approval (org admin + institution admin → 403)
3. Organization rejection (platform admin → `rejected`; pending joins rejected too)
4. Repeated organization decision (second decision → 422)
5. Pending organization access denied
6. Authorized institution approval (org admin → institution `active`)
7. Unauthorized institution approval (platform + institution admin → 403/404)
8. Institution rejection (org admin → institution `rejected`)
9. Repeated join-request decision (→ 409)
10. Pending institution access denied
11. Approved institution access allowed (staff/faculty registration succeeds)
12. Cross-organization approval attempt denied
13. Institution admin receives only institution scope
14. Institution admin cannot access another institution (403)
15. Organization admin scope behavior (manages institutions, cannot approve own org)
16. Phase 6.13.1–6.13.3 regression (all endpoints/repos/authz unchanged)

## 9. Exact Results

```
tests/test_approval_workflow_phase_6_13_4.py      22 passed
tests/test_organization_institution_phase_6_13_1.py  31 passed
tests/test_organization_registration_phase_6_13_2.py  19 passed
tests/test_institution_registration_phase_6_13_3.py   76 passed
---------------------------------------------------------------
Total                                               148 passed, 4 skipped, 0 failures
```

Full backend regression (all test files): **1139 passed, 15 skipped, 0 failures.**
Phase 6.13.1–6.13.3 remain green. No regressions introduced.

## 10. Remaining Limitations

- **Student / faculty / staff registration** — deferred to later phases (out of scope).
- **New login methods** — not addressed (out of scope).
- **Frontend UI** — not addressed (out of scope).
- **Public chatbot redesign / RAG filtering** — not addressed (out of scope).
- **Webhook / notification on approval** — cascade updates rows synchronously but no external notification emitted. Addable later without schema changes.
- **Approval audit log / history table** — decisions recorded on existing `decided_by_user_id` / `decided_at` / `decision_reason` columns. Dedicated immutable audit ledger not created.
- **Bulk approval UI** — cascade (`update_join_requests_for_organization`) handles bulk at data layer; no bulk endpoint exposed.
- **Timeout / expiry of pending requests** — no auto-expiry. Addable via scheduled job or `pg_cron` without schema changes.
- **Appeal / re-submission flow** — rejected organizations/institutions cannot re-submit through existing endpoints. Would require new endpoint + status transition (`rejected → pending`).