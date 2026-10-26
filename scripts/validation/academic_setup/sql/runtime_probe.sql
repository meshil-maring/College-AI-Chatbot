-- Runs only in a future approved container, before bootstrap or migration replay.
DO $$
BEGIN
    IF current_user <> 'postgres' OR session_user <> 'postgres'
        OR current_database() <> 'postgres'
        OR current_setting('server_version_num')::integer <> 170006
        OR current_setting('data_directory') <> '/var/lib/postgresql/data'
        OR current_setting('listen_addresses') <> ''
        OR current_setting('unix_socket_directories') <> '/var/lib/postgresql/data'
        OR current_setting('unix_socket_permissions') <> '0700'
        OR inet_server_addr() IS NOT NULL THEN
        RAISE EXCEPTION 'Isolated socket-only PostgreSQL 17.6 required';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_hba_file_rules
        WHERE error IS NOT NULL OR (type <> 'local' AND auth_method <> 'reject')) THEN
        RAISE EXCEPTION 'Network authentication must be rejected';
    END IF;
END $$;
