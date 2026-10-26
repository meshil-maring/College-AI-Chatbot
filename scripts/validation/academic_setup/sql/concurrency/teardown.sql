-- Finalization, not row deletion: append-only audits and their FK principals
-- remain intentionally until strict owned disposable-container destruction.
BEGIN;
DO $$ BEGIN
    IF (SELECT count(*) FROM academic_setup_check.race_worlds)<>2
        OR (SELECT count(*) FROM academic_setup_check.race_expected_rows
            WHERE relation_name='public.admin_audit_log')<>20
        OR (SELECT count(*) FROM academic_setup_check.race_expected_rows)<>28 THEN
        RAISE EXCEPTION 'Committed fixture registry is incomplete';
    END IF;
END $$;
-- Remove only exact registered rows from the in-memory comparison. Missing or
-- changed fixtures fail closed; no database rows or audit protections change.
SELECT academic_setup_check.verify_post_academic();
COMMIT;
