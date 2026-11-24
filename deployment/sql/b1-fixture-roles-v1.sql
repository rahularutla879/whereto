-- DISPOSABLE restore only, never Supabase. B1 role metadata must first confirm
-- these safe attributes/NULL expiry. No password or platform-admin recreation.
DO $$ BEGIN
 IF current_database()<>'whereto_b1_verify' OR session_user<>'b1_restore_admin'
 OR inet_server_addr() IS NOT NULL THEN RAISE EXCEPTION 'not_isolated_B1_fixture'; END IF;
END $$;
CREATE ROLE postgres LOGIN INHERIT NOSUPERUSER CREATEDB CREATEROLE REPLICATION BYPASSRLS PASSWORD NULL;
CREATE ROLE whereto_plan_runtime LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD NULL;
-- Archive safe source membership metadata, but do NOT impersonate/recreate
-- Supabase's managed administrator graph here. Restored application object ACLs
-- and runtime flags/policies must match; platform-wide recovery is out of scope.
