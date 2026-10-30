# Development browser reliability journey

For the local navigation and responsive-layout check, first build the frontend,
then run `node scripts/validation/academic_workspace/browser/navigation.mjs` from
the repository root. This separate journey uses intercepted fixture responses,
an ephemeral local static server and installed Chrome. It checks direct academic
destinations, the setup guide, calendar tabs, browser history, refresh and mobile
navigation at 1440, 1024, 390 and 320 CSS pixels. It rejects unexpected API calls
and writes screenshots/results under `logs/frontend/academic-navigation/`.
No live account or backend is used for this check.

This journey uses real password authentication, server-issued tokens and the
normal academic APIs. It creates an email-confirmed test administrator only in
the selected active development institution. No invitation or email is sent.
The account's grant is removed and Auth sign-in is blocked in the Python cleanup;
the inactive application identity remains to preserve academic audit records.
Existing administrator credentials are never changed.

Run the backend on `127.0.0.1:18000` with `DEBUG=false`, `ENVIRONMENT=test` and
`EMAIL_ALLOW_LIVE_IN_DEVELOPMENT=false`. Start the test frontend from repository
root with `node scripts/validation/academic_workspace/browser/serve.mjs`.
Install frontend dependencies first. The harness uses `playwright-core` with an
installed Chrome browser, without downloading an additional browser.

From `backend/`, where the development `.env` is discovered:

```powershell
$env:DEBUG='false'
$env:ENVIRONMENT='test'
./.venv/Scripts/python.exe ../scripts/validation/academic_workspace/browser/run.py --institution-id INSTITUTION_UUID
```

Each run creates a unique `E2E` prefix. It saves a department, program, dated year
with two terms, subject, progression stage, draft curriculum, subject mapping,
published curriculum, batch, section and offering through browser forms. It
checks failed-save draft retention, retry uniqueness, real saved relationships,
local token renewal, revoked-session recovery, reload and cross-tab sign-out.
Browser clock acceleration triggers renewal; authentication responses remain real.
Cross-tab renewal with an open draft is not covered by this journey.
To resume after the base catalogue was saved, append
`--resume-prefix E2E1234ABCD` for that run in the same institution. A completed
manifest repeats only the session checks without creating another academic tree.

The academic fixtures remain in the development database, including partially
completed runs. Inspect the run's records manifest before removing any fixtures;
published curriculum and audit history may prevent deletion. Never use this
script with production settings or a production database.

Credentials pass to Node on stdin and are never written to reports. Nonsecret
record manifests, account-cleanup evidence, screenshots and snapshots live in
`logs/frontend/browser/`. Save the command output under `logs/frontend/`.
