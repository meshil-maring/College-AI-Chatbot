-- Injected after the private schema/inventories exist; no psql include commands.
-- Read catalogs only: inspecting a foreign table must never contact its server.
CREATE FUNCTION academic_setup_check.relation_contract(relation_id oid) RETURNS jsonb
LANGUAGE sql SET search_path='' AS $$
    SELECT jsonb_build_object(
        'kind',c.relkind,'owner',pg_get_userbyid(c.relowner),'acl',c.relacl::text,
        'options',c.reloptions,'persistence',c.relpersistence,'access_method',c.relam,
        'rls',c.relrowsecurity,'force_rls',c.relforcerowsecurity,'populated',c.relispopulated,
        'replica_identity',c.relreplident,'tablespace',c.reltablespace,
        'definition',CASE WHEN c.relkind IN ('v','m') THEN pg_get_viewdef(c.oid,false) END,
        'partition_key',CASE WHEN c.relkind='p' THEN pg_get_partkeydef(c.oid) END,
        'partition_bound',pg_get_expr(c.relpartbound,c.oid),
        'parents',(SELECT COALESCE(jsonb_agg(i.inhparent::regclass::text ORDER BY i.inhseqno),'[]'::jsonb)
            FROM pg_inherits i WHERE i.inhrelid=c.oid),
        'columns',(SELECT COALESCE(jsonb_agg(jsonb_build_object(
            'name',a.attname,'type',format_type(a.atttypid,a.atttypmod),'notnull',a.attnotnull,
            'default',pg_get_expr(d.adbin,d.adrelid),'acl',a.attacl::text,
            'identity',a.attidentity,'generated',a.attgenerated,'collation',a.attcollation,
            'foreign_options',a.attfdwoptions)
            ORDER BY a.attnum),'[]'::jsonb) FROM pg_attribute a
            LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
            WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped),
        'foreign',(SELECT jsonb_build_object('server',s.srvname,'options',f.ftoptions,
            'server_owner',pg_get_userbyid(s.srvowner),'server_acl',s.srvacl::text,
            'server_type',s.srvtype,'server_version',s.srvversion,
            'server_options',s.srvoptions,'wrapper',w.fdwname,'wrapper_owner',pg_get_userbyid(w.fdwowner),
            'wrapper_acl',w.fdwacl::text,'handler',w.fdwhandler,'validator',w.fdwvalidator,'wrapper_options',w.fdwoptions)
            FROM pg_foreign_table f JOIN pg_foreign_server s ON s.oid=f.ftserver
            JOIN pg_foreign_data_wrapper w ON w.oid=s.srvfdw WHERE f.ftrelid=c.oid),
        -- Ordinary tables already have projected constraint/index/trigger capture.
        -- Do not fingerprint their new sanctioned parent-side academic FK triggers.
        'constraints',CASE WHEN c.relkind<>'r' THEN (SELECT COALESCE(jsonb_agg(
            jsonb_build_object('name',con.conname,'definition',pg_get_constraintdef(con.oid))
            ORDER BY con.conname),'[]'::jsonb) FROM pg_constraint con WHERE con.conrelid=c.oid) END,
        'indexes',CASE WHEN c.relkind<>'r' THEN (SELECT COALESCE(jsonb_agg(
            jsonb_build_object('name',i.indexrelid::regclass::text,'definition',pg_get_indexdef(i.indexrelid),
                'valid',i.indisvalid,'ready',i.indisready,'clustered',i.indisclustered,
                'replica_identity',i.indisreplident)
            ORDER BY i.indexrelid::regclass::text),'[]'::jsonb)
            FROM pg_index i WHERE i.indrelid=c.oid) END,
        'triggers',CASE WHEN c.relkind<>'r' THEN (SELECT COALESCE(jsonb_agg(jsonb_build_object(
            'name',t.tgname,'enabled',t.tgenabled,'definition',pg_get_triggerdef(t.oid)) ORDER BY t.tgname),
            '[]'::jsonb) FROM pg_trigger t WHERE t.tgrelid=c.oid) END,
        'policies',CASE WHEN c.relkind<>'r' THEN (SELECT COALESCE(jsonb_agg(to_jsonb(p)-'oid' ORDER BY p.polname),
            '[]'::jsonb) FROM pg_policy p WHERE p.polrelid=c.oid) END,
        'rules',(SELECT COALESCE(jsonb_agg(jsonb_build_object('name',r.rulename,
            'enabled',r.ev_enabled,'definition',pg_get_ruledef(r.oid,false)) ORDER BY r.rulename),
            '[]'::jsonb) FROM pg_rewrite r WHERE r.ev_class=c.oid))
    FROM pg_class c WHERE c.oid=relation_id
$$;
CREATE FUNCTION academic_setup_check.catalog_inventory() RETURNS jsonb
LANGUAGE sql SET search_path='' AS $$
    SELECT jsonb_build_object(
        'tables',(SELECT COALESCE(jsonb_object_agg(n.nspname||'.'||c.relname,
            academic_setup_check.relation_contract(c.oid)),'{}'::jsonb)
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE c.relkind IN ('r','p','v','m','f')
                AND (n.nspname='public' OR (n.nspname='auth' AND c.relname='users'))),
        'routines',(SELECT COALESCE(jsonb_object_agg(p.oid::regprocedure::text,
            jsonb_build_object('kind',p.prokind,'owner',pg_get_userbyid(p.proowner),'acl',p.proacl::text,
                'definition',CASE WHEN p.prokind<>'a' THEN pg_get_functiondef(p.oid) END,
                'catalog',to_jsonb(p)-'oid',
                'aggregate',(SELECT to_jsonb(a)-'aggfnoid' FROM pg_aggregate a WHERE a.aggfnoid=p.oid))),
            '{}'::jsonb) FROM pg_proc p WHERE p.pronamespace='public'::regnamespace),
        'sequences',(SELECT COALESCE(jsonb_object_agg(n.nspname||'.'||c.relname,
            jsonb_build_object('kind',c.relkind,'owner',pg_get_userbyid(c.relowner),'acl',c.relacl::text,
                'persistence',c.relpersistence,'definition',to_jsonb(s)-'seqrelid',
                'owned_by',(SELECT COALESCE(jsonb_agg(jsonb_build_object('schema',ns.nspname,
                    'table',parent.relname,'column',a.attname,'dependency',d.deptype)
                    ORDER BY ns.nspname,parent.relname,a.attname),'[]'::jsonb)
                    FROM pg_depend d JOIN pg_class parent ON parent.oid=d.refobjid
                    JOIN pg_namespace ns ON ns.oid=parent.relnamespace
                    JOIN pg_attribute a ON a.attrelid=parent.oid AND a.attnum=d.refobjsubid
                    WHERE d.objid=c.oid AND d.classid='pg_class'::regclass
                        AND d.refclassid='pg_class'::regclass AND d.deptype IN ('a','i')))),'{}'::jsonb)
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_sequence s ON s.seqrelid=c.oid WHERE n.nspname IN ('public','auth')))
$$;
