# Students workspace, registration, invitations, and approval

**CAI-RBAC-001 v1.2; DRAFT - REVIEW ONLY; 21 October 2026.** Read the [reading guide](../README.md) and relevant role first. Source observations are not live-deployment certification.

## Students workspace access

**Session requirement:** Preserve current role permissions when reusing the Students design. Shared components, filters, and navigation must not give Staff the same access as Admin or Faculty.

**Source-observed interface and route behavior:** **S04, S05, S11, S12, S13**

| Students function | Institution Admin | Faculty / Teacher | Staff |
|---|---|---|---|
| Roster | Institution-scoped workspace, subject to required read permissions. | Authorized academic scope. | Not exposed in the current Students workspace. |
| Record history | Institution-scoped student history, subject to read permissions. | History within authorized academic scope. | Not exposed in the current Students workspace. |
| Waiting approval view | Pending student directory and permission-gated approval queue. | Pending students in authorized scope; viewing does not grant approval authority. | Existing institution-scoped approval workflow. |
| Approve / reject | Requires the respective approval or rejection permission. | Not granted by the Faculty role or Faculty Students routes. | Requires the respective permission and institution-scoped Staff eligibility. |
| Register — Single Student | Requires `students.create` and institution scope. | Requires `attendance.manage` and eligible teaching scope. | Not exposed or authorized by the current registration routes. |
| Register — Bulk Import | Same saved-record authorization as individual registration. | Same teaching-scope authorization as individual registration. | No expansion of current access. |
| Send saved-registration invitation | Admin registration authorization plus saved-record scope checks. | Faculty registration authorization plus saved-record scope checks. | No new invitation access. |

Admin and Faculty use shared student components with role-specific API adapters. Their API paths and permission requirements differ. Staff uses the shared approval queue without acquiring the roster, history, or registration features.

Roster filters may narrow Course, Branch, Batch, Section, Semester, status, or search results. A filter does not enlarge the server-authorized dataset. Record history is student/workflow history; access to it does not imply permission to read unrestricted audit logs.

## Registration, invitations, and approval

### Separate records and transitions

| Stage | What it means | What it does not grant |
|---|---|---|
| Class pre-registration | An authorized operator saves the student's identity/contact and class placement. | No automatic authentication account, approved role, subject enrollment, or attendance record. |
| Invitation requested | The operator explicitly chooses automatic sending or sends after saving. | No account approval or sign-in session. |
| Email accepted by provider | The provider has accepted the message for delivery. | No proof of inbox delivery, account creation, or approval. |
| Account registration | The student submits the public account-registration form for an active institution. | No approved academic access while approval remains pending. |
| Approval / rejection | An authorized decision changes the account's eligibility through the approval workflow. | No authority to bypass unrelated identity, tenant, or academic controls. |

**Source-observed:** Class pre-registration and account registration are separate services. Public student/faculty/staff registration does not accept arbitrary roles or scopes, and starts the relevant pending workflow. The class-registration service does not insert subject attendance rosters or subject enrollments. **S11, S14, S15**

### Registration fields and academic placement

- The operator selects Course, Branch, Section, and Batch in the supported academic workflow.
- Batch means the configured admission cohort, such as **2026–2030**, and is stored by batch reference with start/end years; it must not be inferred from the current academic year.
- Academic year and semester remain part of the authorized class context.
- Student name, register number, and a valid email are required by the current class-registration contract; university roll number is optional.
- Subjects are assigned later through their separate authorized workflow.
- An active batch must belong to the selected institution and program/branch.

**Source-observed:** Batch administration currently reuses `departments.manage`; there is no dedicated `batches.manage` code in the inspected catalog. The class path identifies an authorization scope; client-supplied subject IDs do not establish class-registration authority. **S11, S17**

### Invitations

**Session requirements and source-observed behavior:** **S15, S18, S19**

- Automatic invitation email starts **off**. Successful registration offers an explicit send action afterward.
- Only successfully saved registrations may be invited.
- Recipient, institution, identifiers, and class details come from the authorized saved record. A client cannot replace the recipient in the send request.
- An invitation links to the existing student account-registration page. It is not a bearer credential or a one-time account-activation grant.
- Mail failure must not erase the saved registration or require it to be created again.
- Delivery tracking distinguishes failed, pending, locally captured, and provider-accepted results. A sent registration is not automatically resent.
- Claim/completion logic coordinates attempts. This is not a guarantee of provider-level exactly-once delivery.
- Provider acceptance must not be displayed as confirmed inbox delivery.
- SMTP/API credentials, raw provider errors, and invitation secrets must not appear in user-facing failure messages or ordinary logs.

### Bulk import

The proposed workflow is Upload File → Validate and Preview → Confirm Import → Import Result. Each committed row must pass the same authorization and business rules as an individually saved registration.

The system MUST distinguish duplicate rows, invalid fields, conflicts with established records, successful validation, successful persistence, and email delivery outcomes. Valid previews must not be treated as permission to overwrite existing identities. Actor and tenant must be resolved server-side. Changes in grants or academic scope between preview and commit must be handled safely.

### Student account states

An unregistered class entry, pending account, approved active student, rejected registration, and inactive account are distinct states. Student academic-data access MUST require the eligible student context, not merely possession of an authenticated provider account. Users MUST NOT approve their own registration. The complete enforcement of self-approval prevention and every transition remains part of the verification plan. **S14, S20**
