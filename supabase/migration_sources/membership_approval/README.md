# Staff and faculty approval deployment repair

The observed deployment runs the Phase 7.24 approval function, while the backend
expects the later `role_granted` and `audit_persisted` result on initial and repeat
approval. The old function commits approval but omits those fields, so the backend
stops before confirming the Auth email. The rejection RPC is also absent.

These sources repair those two contracts without installing the unrelated B05
invitation draft. Already-installed B05 implementations are preserved. Approval,
the exact institution role and the audit commit together; provider email
confirmation follows in the backend. Repeating approval revalidates the actor,
tenant, applicant and existing grant before repairing the audit. It cannot restore
a revoked role or move a role between institutions. Rejection grants and revokes
nothing. Both routines remain service-role-only.

Generate with `python scripts/maintenance/migrations/build_membership_approval.py`
and check parity with `--check`. The generated migration is transactional and
reloads the PostgREST schema cache. It does not confirm emails or change existing
decisions. After applying it, retry sign-in setup for the approved request through
the existing institution-admin approval endpoint.

Validate SQL with `python scripts/validation/membership_approval/verify.py`.
The validator uses a new owned, isolated PostgreSQL container and synthetic
accounts; application tests separately cover provider confirmation and login.
