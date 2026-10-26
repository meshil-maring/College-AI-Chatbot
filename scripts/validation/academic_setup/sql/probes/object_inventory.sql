-- Future PostgreSQL negative controls. Nothing in this file has been executed.
BEGIN;
SELECT academic_setup_check.verify_post_academic();
CREATE TABLE public.academic_retained_inventory_probe(id integer);
CREATE FUNCTION public.academic_retained_inventory_probe() RETURNS integer LANGUAGE sql AS 'SELECT 1';
CREATE SEQUENCE public.academic_retained_inventory_sequence;
-- Include a harmless retained object in both baselines only for this transaction.
UPDATE academic_setup_check.snapshots
SET value=academic_setup_check.capture(name='post_decommission_catalog')
WHERE name IN ('post_decommission','post_decommission_catalog');
SELECT academic_setup_check.verify_post_academic();
DO $$
DECLARE item record; baseline jsonb:=academic_setup_check.capture(true);
BEGIN
    FOR item IN SELECT * FROM (VALUES
        ('CREATE TABLE public.academic_unexpected_probe(id integer)','P4201',
            'Unexpected added academic catalog object'),
        ('CREATE TABLE public.academic_unexpected_probe(id integer) PARTITION BY RANGE(id)','P4201',
            'Unexpected added academic catalog object'),
        ('CREATE FUNCTION public.academic_unexpected_probe() RETURNS integer LANGUAGE sql AS ''SELECT 1''',
            'P4201','Unexpected added academic catalog object'),
        ('CREATE PROCEDURE public.academic_unexpected_probe() LANGUAGE plpgsql AS ''BEGIN NULL; END''',
            'P4201','Unexpected added academic catalog object'),
        ('CREATE SEQUENCE public.academic_unexpected_probe','P4201',
            'Unexpected added academic catalog object'),
        ('ALTER TABLE public.academic_retained_inventory_probe ADD COLUMN note text','P4202',
            'Retained object changed during Academic Setup replay'),
        ('DROP TABLE public.academic_retained_inventory_probe','P4202','Retained catalog object removed'),
        ('CREATE OR REPLACE FUNCTION public.academic_retained_inventory_probe() RETURNS integer '
            'LANGUAGE sql AS ''SELECT 2''','P4202','Retained object changed during Academic Setup replay'),
        ('DROP FUNCTION public.academic_retained_inventory_probe()','P4202','Retained catalog object removed'),
        ('ALTER SEQUENCE public.academic_retained_inventory_sequence INCREMENT BY 2','P4202',
            'Retained object changed during Academic Setup replay'),
        ('DROP SEQUENCE public.academic_retained_inventory_sequence','P4202','Retained catalog object removed')
    ) cases(command,state,message) LOOP
        BEGIN
            EXECUTE item.command;
            PERFORM academic_setup_check.expect_error(
                'SELECT academic_setup_check.verify_post_academic()',item.state,item.message);
            RAISE EXCEPTION USING ERRCODE='P4099';
        EXCEPTION WHEN SQLSTATE 'P4099' THEN NULL;
        END;
        IF academic_setup_check.capture(true) IS DISTINCT FROM baseline THEN
            RAISE EXCEPTION 'Inventory negative control did not restore original state';
        END IF;
    END LOOP;
    PERFORM academic_setup_check.expect_error(
        'SELECT academic_setup_check.assert_catalog_inventory(NULL,NULL)','P4202','Catalog inventory missing');
    PERFORM academic_setup_check.verify_post_academic();
END $$;
ROLLBACK;
