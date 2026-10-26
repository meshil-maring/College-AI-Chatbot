-- An actual decommission preflight violation: unexpected preserved-table FK.
BEGIN;
CREATE TABLE public.academic_setup_unexpected_consumer (
    program_id uuid REFERENCES public.programs(program_id)
);
UPDATE academic_setup_check.snapshots
SET value=academic_setup_check.capture(true) WHERE name='rollback';
COMMIT;
