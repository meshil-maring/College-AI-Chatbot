BEGIN;
SET LOCAL request.jwt.claim.role='service_role';
SELECT academic_setup_check.verify_post_academic();
CREATE TABLE academic_setup_check.race_worlds(name text PRIMARY KEY,value jsonb NOT NULL);
CREATE TABLE academic_setup_check.race_expected_rows(relation_name text NOT NULL,row_data jsonb NOT NULL,
    PRIMARY KEY(relation_name,row_data));
INSERT INTO academic_setup_check.race_worlds VALUES
    ('a',academic_setup_check.world()),('b',academic_setup_check.world());
DO $$
DECLARE w jsonb; r jsonb;
BEGIN
    SELECT value INTO STRICT w FROM academic_setup_check.race_worlds WHERE name='a';
    r:=academic_setup_check.mutate(w,'departments','{"name":"Race parent","code":"RACE_PARENT"}');
    UPDATE academic_setup_check.race_worlds
    SET value=w||jsonb_build_object('race_parent',r->'department_id','race_parent_before',r)
    WHERE name='a';
END $$;
-- Record exact fixture rows, not a tenant-wide exemption or a new baseline.
INSERT INTO academic_setup_check.race_expected_rows
SELECT 'public.institutions',to_jsonb(t) FROM public.institutions t
WHERE institution_id IN (SELECT (value->>'tenant')::uuid FROM academic_setup_check.race_worlds)
UNION ALL
SELECT 'public.users',to_jsonb(t) FROM public.users t
WHERE id IN (SELECT (value->>'actor')::uuid FROM academic_setup_check.race_worlds)
UNION ALL
SELECT 'auth.users',to_jsonb(t) FROM auth.users t
WHERE id IN (SELECT (value->>'auth')::uuid FROM academic_setup_check.race_worlds)
UNION ALL
SELECT 'public.user_roles',to_jsonb(t) FROM public.user_roles t
WHERE user_id IN (SELECT (value->>'actor')::uuid FROM academic_setup_check.race_worlds)
UNION ALL
SELECT 'public.admin_audit_log',to_jsonb(t) FROM public.admin_audit_log t
WHERE institution_id IN (SELECT (value->>'tenant')::uuid FROM academic_setup_check.race_worlds);
DO $$ BEGIN
    IF (SELECT count(*) FROM academic_setup_check.race_expected_rows WHERE relation_name='public.admin_audit_log')<>15
        OR (SELECT count(*) FROM academic_setup_check.race_expected_rows WHERE relation_name<>'public.admin_audit_log')<>8 THEN
        RAISE EXCEPTION 'Unexpected committed fixture footprint';
    END IF;
END $$;
CREATE FUNCTION academic_setup_check.project_race_rows(current_state jsonb) RETURNS jsonb
LANGUAGE plpgsql SET search_path='' AS $$
DECLARE projected_relation text; item record; projected jsonb;
BEGIN
    IF EXISTS (SELECT 1 FROM academic_setup_check.race_expected_rows r
        WHERE r.relation_name NOT IN ('public.institutions','public.users','auth.users',
            'public.user_roles','public.admin_audit_log')) THEN
        RAISE EXCEPTION 'Unexpected fixture projection relation';
    END IF;
    FOR item IN SELECT * FROM academic_setup_check.race_expected_rows LOOP
        IF (SELECT count(*) FROM jsonb_array_elements(current_state->'tables'->item.relation_name->'rows') v
            WHERE v=item.row_data)<>1 THEN
            RAISE EXCEPTION 'Recorded committed fixture row changed or disappeared';
        END IF;
    END LOOP;
    FOR projected_relation IN SELECT DISTINCT r.relation_name FROM academic_setup_check.race_expected_rows r LOOP
        SELECT COALESCE(jsonb_agg(v ORDER BY v::text),'[]'::jsonb) INTO projected
        FROM jsonb_array_elements(current_state->'tables'->projected_relation->'rows') v
        WHERE NOT EXISTS (SELECT 1 FROM academic_setup_check.race_expected_rows r
            WHERE r.relation_name=projected_relation AND r.row_data=v);
        current_state:=jsonb_set(current_state,ARRAY['tables',projected_relation,'rows'],projected);
    END LOOP;
    RETURN current_state;
END $$;
REVOKE ALL ON academic_setup_check.race_worlds FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON academic_setup_check.race_expected_rows FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION academic_setup_check.project_race_rows(jsonb) FROM PUBLIC,anon,authenticated,service_role;
COMMIT;
