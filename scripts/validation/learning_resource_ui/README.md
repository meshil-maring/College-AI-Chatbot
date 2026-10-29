# Learning resource browser verification

Start the frontend on loopback, then run from the repository root:

```powershell
node scripts/validation/learning_resource_ui/verify.mjs http://127.0.0.1:5180
```

Uses the frontend's installed `playwright-core` and local Microsoft Edge in
headless mode. Every API request is intercepted with fictional data. Remote
requests are blocked; the harness never reads credentials, contacts a configured
backend or changes a project database.

Exercises the same page in all three workspaces, draft audience selection,
upload/index/submit, admin confirmation/approval/publication/unpublication,
unsaved-change recovery, modal focus and reflow at 1440, 1024, 390 and 320 pixels.
The fixture checks expected revision/source-policy tokens and multipart upload
shape. Screenshots and results belong in `logs/frontend/learning-resource-ui/`.
This mode verifies browser/HTTP contracts independently of the backend.

For real FastAPI and PostgreSQL workflow verification, leave the same frontend
running and use the backend environment from the repository root:

```powershell
backend/.venv/Scripts/python.exe scripts/validation/learning_resource_ui/live.py http://127.0.0.1:5180
```

`live.py` replays migrations and seeds fictional institution roles in an owned,
network-isolated, temporary PostgreSQL container using the cached image and
ownership checks in `../academic_workspace/runtime.py`. It does not use the
configured local or hosted project database. The temporary API binds only to
loopback and closes with its client/server and container even on failure.

`database_adapter.py` executes the actual workflow functions as `service_role`,
preserving actor/tenant/grant checks and revision/policy concurrency guards.
`api_server.py` uses the real resource/chat/history routes, schemas and errors.
`table_adapter.py` transports actual conversation/message repository operations
to PostgreSQL. `chat_adapter.py` runs the real retrieval and generation services
with fixed local embedding/generation providers. Keyed turns execute actual atomic
message, AI-response, retrieval and citation persistence. Legacy unkeyed requests
retain the existing background boundary.
Only identity-provider resolution, object storage and external model work
use fictional local substitutes. The API permissions come from the seeded
database grants; they are not wildcard role fixtures. The setup publishes a
public handbook through actual HTTP calls before running the three browser
journeys. No configured credentials or external provider calls are required.
Browser journeys ask about a selected resource, send follow-ups, reload and
restore the same scoped conversation from the ordinary assistant's history.
The chat journey compares live and restored citation cards after reload, including
titles, quotes and scores, and checks their layout at 320 pixels wide.
`recovery_journey.mjs` deliberately drops a committed HTTP response, checks and
replays it, then retries a failed question after reload with the same turn ID.
It verifies saved-message counts and recovery layout at narrow viewport widths.

These checks complement `../knowledge_revisions/` and do not verify deployed
authentication, object storage or model providers in a staging environment.
