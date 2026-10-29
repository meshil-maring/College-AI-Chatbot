"""Prove an audience edit invalidates a review token across real SQL sessions."""

import subprocess
import time

from academic_workspace.runtime import execute, sql_arguments


def verify_stale_review(container):
    editor = subprocess.Popen(
        sql_arguments(container), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding="utf-8",
    )
    editor.stdin.write("""
        SET application_name = 'knowledge-revision-audience-edit';
        BEGIN;
        INSERT INTO public.knowledge_source_revision_audiences
            VALUES (knowledge_fixture.id('race_rev'), 'faculty');
        SELECT pg_sleep(2);
        COMMIT;
    """)
    editor.stdin.close()
    editor.stdin = None
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            ready = execute(container, """
                SELECT EXISTS(SELECT 1 FROM pg_stat_activity
                    WHERE application_name = 'knowledge-revision-audience-edit'
                        AND wait_event = 'PgSleep')
            """)
            if ready == "t":
                break
            if editor.poll() is not None:
                raise RuntimeError("Audience editor exited before the race probe")
            time.sleep(0.1)
        else:
            raise RuntimeError("Audience edit did not acquire the revision lock")
        execute(container, """
            UPDATE public.knowledge_source_revisions
                SET lifecycle_status = 'under_review', submitted_at = now()
                WHERE revision_id = knowledge_fixture.id('race_rev')
                    AND revision_version = (SELECT expected FROM knowledge_fixture.review_tokens);
            SELECT knowledge_fixture.assert_true('Concurrent edit invalidates stale review token',
                (SELECT lifecycle_status = 'draft'
                    AND revision_version > (SELECT expected FROM knowledge_fixture.review_tokens)
                 FROM public.knowledge_source_revisions
                 WHERE revision_id = knowledge_fixture.id('race_rev')));
        """)
        print("PASS: concurrent audience edit rejects stale review token", flush=True)
    finally:
        output, error = editor.communicate(timeout=30)
        if editor.returncode:
            raise RuntimeError(error or output or "Audience editor failed")
