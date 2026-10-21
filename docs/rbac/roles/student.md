# Student

**Status: DRAFT — REVIEW ONLY. Canonical role: `student`.** Read [shared rules](../shared-rules.md). Rules below are proposed except explicitly source-observed behavior.

## Account and resource scope

Personal academic access requires an eligible student identity in the authorized institution. Ownership MUST be resolved from the authenticated application user, not a submitted student ID.

**Source-observed — S20:** The student-context service resolves the student profile server-side and checks approval, activity, and institution eligibility. Possessing a provider account or being listed in a class is not enough for approved academic access.

## Allowed actions

| Action | Relevant permission | Scope |
|---|---|---|
| Read/update permitted profile fields | `profile.own.read`, `profile.own.update` | Own profile; authoritative identifiers and authorization fields excluded. |
| Read attendance and results | `attendance.own.read`, `results.own.read` | Own eligible academic records. |
| Read notices and learning resources | `notices.read`, `documents.read` | Permitted audience, institution, and resource visibility. |
| Read/update notification state | `notifications.own.read`, `notifications.own.update` | Own notifications. |
| Use authenticated AI chat | `ai.chat` | Own conversations and authorized retrieval. |

Permission presence does not establish that every listed action has an implemented endpoint. Account recovery uses the supported authentication workflow rather than granting administrative permission.

## Restrictions

- No other student's private records or conversations.
- No attendance marking, result editing, account approvals, role/permission changes, or institution reassignment.
- No self-approval or informal identity repair through profile updates.
- Pending, rejected, inactive, or suspended states do not gain approved-student privileges.

## Registration and login

A class record, invitation, account signup, and account approval are separate stages. Invitations request student registration with the institution code preserved; an existing browser account must be switched explicitly. They do not grant an authenticated session, role, or approval. See the [shared registration workflow](../workflows/student-registration.md).

## Bootstrap permissions

**Source-observed (S02):** 9 codes in the local bootstrap map. These are not effective live grants or proof of endpoint availability. The [complete matrix](../permission-catalog.md) is the cross-role reference.

- **Profile:** `profile.own.read`, `profile.own.update`.
- **Notifications:** `notifications.own.read`, `notifications.own.update`.
- **Attendance:** `attendance.own.read`.
- **Results:** `results.own.read`.
- **Documents:** `documents.read`.
- **Notices:** `notices.read`.
- **AI:** `ai.chat`.

## Relevant review cases

V02, V06, V12, V15, V17, and V20 cover eligibility, ownership, batch/identity integrity, session switching, revocation, and injected authority. See [verification](../verification.md).

## Sources

S01–S03, S11, S14–S16, S19, and S20 in [source references](../source-references.md). Consult the [permission catalog](../permission-catalog.md) only for cross-role comparisons or definition changes.
