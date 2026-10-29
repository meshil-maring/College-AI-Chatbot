"""Real API + PostgreSQL browser journey with no project database access."""

import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
sys.path[:0] = [str(ROOT / "scripts/validation"), str(ROOT / "backend")]
os.environ.update(DEBUG="false", ENVIRONMENT="test", EMAIL_ALLOW_LIVE_IN_DEVELOPMENT="false",
                  SUPABASE_URL="", SUPABASE_SECRET_KEY="", SUPABASE_PUBLISHABLE_KEY="",
                  R2_ACCESS_KEY_ID="", R2_SECRET_ACCESS_KEY="", OPENROUTER_API_KEY="")

from academic_workspace.runtime import database, execute
from database_adapter import DatabaseAdapter
from api_server import serve

MIGRATION = "20261028010000_knowledge_audience_revisions.sql"


def seed(container):
    migrations = ROOT / 'supabase/migrations'
    statements = [path.read_text(encoding='utf-8') for path in sorted(migrations.glob('*.sql'))
                  if path.name < MIGRATION]
    fixtures = ROOT / "scripts/validation/knowledge_revisions"
    statements.extend(path.read_text(encoding='utf-8') for path in [
        fixtures / 'seed.sql', migrations / MIGRATION, fixtures / 'workflow/seed.sql',
        migrations / '20261029000000_resource_scoped_conversations.sql',
        migrations / '20261029010000_chat_turn_recovery.sql',
        migrations / '20261029020000_history_citations.sql',
    ])
    # Reconnect between files to preserve their original session settings as
    # well as transactions, without launching a Docker process for each file.
    execute(container, '\n\\connect postgres\n'.join(statements))
    print("PASS: migration replay and fictional role fixtures", flush=True)


def initial_resource(client):
    headers = {"Authorization": "Bearer fixture-admin"}

    def accepted(response, expected=200):
        if response.status_code != expected:
            raise RuntimeError(f"Fixture setup: {response.status_code}: {response.text}")
        return response.json()

    revision = accepted(client.post("/api/v1/knowledge/resources", headers=headers, json={
        "title": "Student support handbook", "source_type": "handbook",
        "description": "Fictional institution handbook for isolated browser validation.",
        "audience": {"mode": "public", "roles": []},
    }), 201)
    base = "/api/v1/knowledge/revisions/" + revision["revision_id"]
    revision = accepted(client.post(base + "/documents", headers=headers,
        data={"expected_version": revision["revision_version"]},
        files={"file": ("handbook.txt", b"Fictional campus support and library opening hours.", "text/plain")}), 201)
    for action in ("submit", "approve", "publish"):
        revision = accepted(client.post(base + "/" + action, headers=headers, json={
            "expected_version": revision["revision_version"], "expected_policy": revision["policy_version"],
        }))
    print("PASS: real API create, multipart upload, submit, approve and publish", flush=True)


def main():
    origin = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5180"
    parsed = urlparse(origin)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("Loopback HTTP UI only")
    with database(purpose="knowledge-resources") as container:
        seed(container)
        with serve(DatabaseAdapter(container)) as (client, backend):
            initial_resource(client)
            subprocess.run(["node", str(HERE / "verify.mjs"), origin, "--backend", backend], check=True)
    print("PASS: real API/SQL browser workflow; run-owned container removed", flush=True)


if __name__ == "__main__":
    main()
