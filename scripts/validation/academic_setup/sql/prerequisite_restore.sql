BEGIN;
DROP TABLE public.academic_setup_unexpected_consumer;
UPDATE academic_setup_check.snapshots
SET value=academic_setup_check.capture(true) WHERE name='rollback';
COMMIT;
