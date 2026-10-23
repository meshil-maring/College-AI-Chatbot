"""Render guarded SQL artifacts; this module never opens a database connection."""

from __future__ import annotations

import json


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def guard(inspection: dict) -> str:
    expected = literal(json.dumps(inspection, separators=(",", ":")))
    return f"""BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '120s';
SELECT pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('academic-decommission:rjnfmjcvkfotneswpygr',0));
LOCK TABLE supabase_migrations.schema_migrations IN ACCESS EXCLUSIVE MODE;
DO $release_guard$
DECLARE expected jsonb := {expected}::jsonb; item record; row_count bigint; fingerprint text; observed jsonb;
BEGIN
    IF current_user <> 'postgres' OR current_database() <> 'postgres' THEN
        RAISE EXCEPTION 'Unexpected database principal or database; release refused';
    END IF;
    SELECT COALESCE(jsonb_agg(version ORDER BY version),'[]'::jsonb) INTO observed
    FROM supabase_migrations.schema_migrations;
    IF observed IS DISTINCT FROM expected->'ledger' THEN
        RAISE EXCEPTION 'Migration ledger changed; release refused';
    END IF;
    SELECT jsonb_agg(jsonb_build_object('name',column_name,'type',data_type,'nullable',is_nullable,
        'default',column_default) ORDER BY ordinal_position) INTO observed FROM information_schema.columns
    WHERE table_schema='supabase_migrations' AND table_name='schema_migrations';
    IF observed IS DISTINCT FROM expected->'ledger_columns' THEN
        RAISE EXCEPTION 'Migration ledger contract changed; release refused';
    END IF;
    FOR item IN SELECT * FROM jsonb_to_recordset(expected->'tables')
        AS t(schema_name text,table_name text,row_count bigint,fingerprint text) ORDER BY schema_name,table_name LOOP
        EXECUTE format('LOCK TABLE %I.%I IN ACCESS EXCLUSIVE MODE',item.schema_name,item.table_name);
    END LOOP;
    SELECT COALESCE(jsonb_agg(jsonb_build_object('institution_id',institution_id,'code',code)
        ORDER BY institution_id),'[]'::jsonb) INTO observed FROM public.institutions;
    IF observed IS DISTINCT FROM expected->'institutions' THEN
        RAISE EXCEPTION 'Institution scope changed; release refused';
    END IF;
    SELECT jsonb_agg(jsonb_build_object('schema_name',n.nspname,'table_name',c.relname)
        ORDER BY n.nspname,c.relname) INTO observed FROM pg_catalog.pg_class c
    JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='r'
      AND (n.nspname='public' OR (n.nspname='auth' AND c.relname='users'));
    IF observed IS DISTINCT FROM (SELECT jsonb_agg(jsonb_build_object('schema_name',t->>'schema_name',
        'table_name',t->>'table_name') ORDER BY t->>'schema_name',t->>'table_name')
        FROM jsonb_array_elements(expected->'tables') t) THEN
        RAISE EXCEPTION 'Application table inventory changed; release refused';
    END IF;
    FOR item IN SELECT * FROM jsonb_to_recordset(expected->'tables')
        AS t(schema_name text,table_name text,row_count bigint,fingerprint text) LOOP
        EXECUTE format('SELECT count(*),md5(COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),''[]''::jsonb)::text) FROM %I.%I t',
            item.schema_name,item.table_name) INTO row_count,fingerprint;
        IF row_count IS DISTINCT FROM item.row_count OR fingerprint IS DISTINCT FROM item.fingerprint THEN
            RAISE EXCEPTION 'Inspected data changed in %.%; release refused',item.schema_name,item.table_name;
        END IF;
    END LOOP;
    SELECT COALESCE(jsonb_agg(jsonb_build_object('identity',p.oid::regprocedure::text,
        'fingerprint',md5(pg_get_functiondef(p.oid))) ORDER BY p.oid::regprocedure::text),'[]'::jsonb)
        INTO observed FROM pg_catalog.pg_proc p WHERE p.pronamespace='public'::regnamespace AND p.prokind='f';
    IF observed IS DISTINCT FROM expected->'routines' THEN
        RAISE EXCEPTION 'Application routine inventory changed; release refused';
    END IF;
END;
$release_guard$;
"""


def ledger_insert(migration: str, columns: list[dict], version: str, name: str) -> str:
    values = {
        "version": literal(version),
        "name": literal(name),
        "statements": "ARRAY[" + literal(migration) + "]::text[]",
    }
    selected = [column["name"] for column in columns if column["name"] in values]
    return (
        "INSERT INTO supabase_migrations.schema_migrations ("
        + ",".join(selected)
        + ") VALUES ("
        + ",".join(values[key] for key in selected)
        + ");\n"
    )


def summary(version: str, migration_hash: str, ending: str) -> str:
    return f"""SELECT jsonb_build_object(
    'migration_version',{literal(version)},'migration_sha256',{literal(migration_hash)},'transaction_end',{literal(ending)},
    'retired_table_count',(SELECT count(*) FROM academic_decommission_tables),
    'remaining_retired_tables',(SELECT count(*) FROM academic_decommission_tables WHERE to_regclass(format('public.%I',name)) IS NOT NULL),
    'retired_routine_name_count',(SELECT count(*) FROM academic_decommission_functions),
    'remaining_retired_routines',(SELECT count(*) FROM pg_catalog.pg_proc p WHERE p.pronamespace='public'::regnamespace
        AND p.proname IN(SELECT name FROM academic_decommission_functions)),
    'retired_permission_count',(SELECT count(*) FROM academic_decommission_permissions),
    'preserved_table_count',(SELECT count(*) FROM academic_decommission_preserved),
    'preserved_row_count',(SELECT sum(jsonb_array_length(rows)) FROM academic_decommission_preserved),
    'auth_user_count',(SELECT count(*) FROM auth.users),'application_user_count',(SELECT count(*) FROM public.users),
    'user_role_count',(SELECT count(*) FROM public.user_roles),'institution_count',(SELECT count(*) FROM public.institutions),
    'student_identity_count',(SELECT count(*) FROM public.students),
    'approval_rpc_present',to_regprocedure('public.b05_approve_student(uuid,uuid,uuid,uuid)') IS NOT NULL,
    'ledger_version_exists',EXISTS(SELECT 1 FROM supabase_migrations.schema_migrations WHERE version={literal(version)})
) AS academic_decommission_release;
{ending};
"""
