"""Replay the database model in run-owned PostgreSQL, never a configured project."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/validation"))

from academic_workspace.runtime import database, execute
from concurrency import verify_stale_review
from turn_concurrency import verify_turn_race

MIGRATION = "20261028010000_knowledge_audience_revisions.sql"
HERE = Path(__file__).parent


def run_file(container, name):
    execute(container, (HERE / name).read_text(encoding="utf-8"))
    print(f"PASS {name}", flush=True)


def verify_migration_rollback(container, migration):
    probe = "DO $$ BEGIN RAISE EXCEPTION 'knowledge rollback probe'; END; $$;\nCOMMIT;"
    tampered = migration.rsplit("COMMIT;", 1)[0] + probe
    try:
        execute(container, tampered)
    except RuntimeError as failure:
        if "knowledge rollback probe" not in str(failure):
            raise
    else:
        raise RuntimeError("Expected the injected migration failure")
    intact = execute(container, """
        SELECT to_regclass('public.knowledge_source_revisions') IS NULL
            AND NOT EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'knowledge_sources'
                    AND column_name IN ('published_revision_id', 'policy_version'))
            AND NOT EXISTS (SELECT 1 FROM knowledge_fixture.original_sources original
                JOIN public.knowledge_sources source USING (knowledge_source_id)
                WHERE original.data IS DISTINCT FROM to_jsonb(source))
    """)
    if intact != "t":
        raise RuntimeError("Failed migration did not roll back cleanly")
    print("PASS: failed migration rolls back schema and legacy data", flush=True)


def main():
    subprocess.run([
        sys.executable, str(ROOT / "scripts/maintenance/migrations/build_knowledge_revisions.py"),
        "--check",
    ], check=True)
    with database(purpose="knowledge-resources") as container:
        folder = ROOT / "supabase/migrations"
        for path in sorted(folder.glob("*.sql")):
            if path.name >= MIGRATION:
                continue
            print(f"REPLAY {path.name}", flush=True)
            execute(container, path.read_text(encoding="utf-8"))
        run_file(container, "seed.sql")
        migration = (folder / MIGRATION).read_text(encoding="utf-8")
        verify_migration_rollback(container, migration)
        execute(container, migration)
        for name in ("helpers.sql", "backfill.sql", "relationships.sql", "lifecycle.sql", "security.sql"):
            run_file(container, name)
        verify_stale_review(container)
        for name in ('workflow/seed.sql', 'workflow/writes.sql', 'workflow/reads.sql',
                     'workflow/history.sql', 'workflow/service_transactions.sql'):
            run_file(container, name)
        execute(container, (folder / '20261029000000_resource_scoped_conversations.sql').read_text(encoding='utf-8'))
        run_file(container, 'workflow/resource_chat.sql')
        execute(container, (folder / '20261029010000_chat_turn_recovery.sql').read_text(encoding='utf-8'))
        run_file(container, 'workflow/chat_turns.sql')
        run_file(container, 'workflow/turn_failures.sql')
        verify_turn_race(container)
        execute(container, (folder / '20261029020000_history_citations.sql').read_text(encoding='utf-8'))
        run_file(container, 'workflow/history_citations.sql')
        print(execute(container, "SELECT count(*) || ' database assertions passed' FROM knowledge_fixture.results"))
    print("PASS: knowledge revision model verified; run-owned container removed", flush=True)


if __name__ == "__main__":
    main()
