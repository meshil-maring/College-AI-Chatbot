# Student registration and institution approval

## Application flow

1. Open the university gateway at `/u/quest123` and choose **Register as Student**.
   The direct registration URL is
   `/login/student?institution=QUEST123&register=1`. The university code remains
   prefilled and is verified through the public lookup endpoint.
2. Enter a name, email, at least one academic number, and matching passwords.
   Submission creates a pending student account and does not sign the student in.
   Complete Supabase email verification if it is enabled for the project; email
   verification and institution approval are separate requirements.
3. An institution administrator opens **Approvals** and selects
   **Refresh registrations** to see new submissions. Authorized staff can use
   the same workflow in their own institution.
4. **Approve** commits the approval state, institution-scoped student role and
   decision audit in one database transaction. **Reject** preserves the account
   and records the rejected state; it does not grant student access.
5. After approval and any required email verification, the student can sign in
   with their email or with either academic number plus the university code.
   Pending and rejected students remain unable to sign in.

## Database deployment required

The connected project's read-only API schema inspection found that
`public.b05_approve_student(uuid, uuid, uuid, uuid)` and
`admin_audit_log.decision_key` are missing. The application already depends on
this transaction for approvals. Application health alone does not verify this
database capability.

The focused repair is
[`20261019000000_student_approval_deployment_repair.sql`](../../supabase/migrations/20261019000000_student_approval_deployment_repair.sql).
It adds the audit idempotency key and unique index, installs the existing
approval transaction, restricts execution to the service role and reloads the
API schema. It does not create, approve, reject, or remove any student account.
It can be applied to the current project without deploying unrelated invitation
changes from the earlier B05 source migration.

Apply this file through authorized Supabase management access or run its full
contents in the target project's SQL Editor. The application API credentials
are insufficient for database DDL. No live migration was performed during the
application implementation.

After applying it, verify:

```sql
SELECT to_regprocedure('public.b05_approve_student(uuid,uuid,uuid,uuid)') IS NOT NULL
    AS approval_function_installed;

SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'admin_audit_log'
      AND column_name = 'decision_key'
) AS audit_key_installed;
```

Both results must be true. Complete a registration with a real student-owned
email, approve it using the university administrator's own session, and sign in
as that student to verify the provider's email configuration and live database
transaction together.

## Verification and limits

The application journey tests use real HTTP routes, services and repositories
with in-memory replacements for Supabase clients. They exercise pending
registration, duplicate rejection, the institution queue, approve/reject and
all three student login identifiers. Existing tests cover authorization, tenant
isolation, compensation and incomplete approval transactions. Frontend checks
cover direct registration entry, preserved university context, queue refresh
and retrying an uncertain approval.

These tests do not send email, modify the connected database, or substitute
for running the SQL migration on PostgreSQL and verifying a live student login.
