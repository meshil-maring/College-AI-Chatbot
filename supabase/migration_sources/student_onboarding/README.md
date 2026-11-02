# Student onboarding invitations

This additive workflow provisions students through an institution-admin invitation
bound to an active academic section. It does not change public self-registration,
which continues to require the existing student approval process.

The invitation stores student identity and a provisional section assignment while
the student is unverified. Only a SHA-256 digest of the random setup-link token is
stored. The email link uses a URL fragment so the token is not sent in HTTP
requests, referrers, or ordinary access logs. Reading the invitation never
consumes the token; the completion RPC rechecks its digest and expiry atomically.

After the student sets a password, the backend creates the confirmed Auth
identity. One database transaction creates the public identity/profile,
provisions the student role through the existing approval command, assigns the
student to the selected section, records the invitation acceptance, and audits
the operation. Capacity and active academic ancestry are checked again at that
point. A section that became inactive must be reassigned before completion.

The admin API supports invitation listing, single invitation creation, safe
resend (maximum three per hour), section reassignment, pending invitation edits,
and cancellation before account setup begins. Invitation email is immutable;
cancel and recreate an invite to use a different address. Bulk CSV/XLSX import
uses the same single-student command for each reviewed row; row outcomes are
independent and explicitly reported.

Generate using `python scripts/maintenance/student_onboarding/build_migration.py`;
use `--check` to verify parity. Generation does not deploy SQL. Review the
target migration history before applying it.
