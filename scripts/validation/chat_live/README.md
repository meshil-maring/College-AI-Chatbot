# Configured-service chat acceptance

Run from `backend/` with development/test configuration:

```powershell
$env:DEBUG='false'
$env:EMAIL_ALLOW_LIVE_IN_DEVELOPMENT='false'
.venv/Scripts/python.exe ../scripts/validation/chat_live/run.py --institution-id UUID --institution-code CODE --source-id PUBLIC_HOSTEL_SOURCE_UUID
```

Uses the configured Supabase Auth/database, R2 storage, embedding service and
generation provider. Starts an owned loopback API with the actual application;
no auth, retrieval, storage or generation dependency is substituted. Creates
four email-confirmed test identities with random passwords held only in memory.
No invitation or password-recovery email is sent. Existing credentials are never
changed. Refuses non-development/test settings.

The run-owned text resource exercises upload/indexing, draft review, publication,
audience restrictions, resource chat, durable replay and restored citations.
It is unpublished in cleanup. Test accounts are made inactive, all of their
grants removed, and their Auth sign-in blocked. Their records, the unpublished
resource, stored file, conversations and audit trail remain for inspection.
Existing resource metadata is compared before and after. A manifest records
every created identifier and cleanup outcome under `logs/backend/live-chat-acceptance/`;
credentials and tokens are never written there.

The real browser phase starts its own Vite server and headless Microsoft Edge,
using the installed frontend dependencies. Public, admin, faculty, staff and
student journeys display cited answers, reload history and check 320px layout.
Screenshots live under `logs/frontend/live-chat-acceptance/<run>/`. Both owned
servers and the browser close in cleanup. This is a manual acceptance runner;
it performs billable provider calls and must not be added to ordinary pytest/CI.

Publication authority does not bypass audience membership: even administrators
cannot consume a staff-only source through the resource library or chatbot.
The student fixture includes an approved profile and is deactivated in cleanup.

For an embedding/generation failure, the API journey checks the durable status
and explicitly retries the same ID at most twice, only after a confirmed failed,
retryable state. Each failure and recovery is recorded in the manifest. This
exercises the application's manual recovery protocol without changing its retry
policy or hiding persistent failures.

After a completed API/audience journey, `--browser-only` verifies auth, the
existing public document and browser flows without creating another resource.
It still owns and disables its four test identities. Compare its manifest with
the API journey's manifest when recording acceptance across separate runs.
