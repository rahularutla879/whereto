"""Explicit administrative CLI; never imported by FastAPI or ordinary startup.

SQL files are trusted repository code. No down/reset command is provided.
"""
import argparse
from hashlib import sha256
import os
from pathlib import Path
import re

import psycopg

from backend.database_check import DatabaseCheckError, connection_settings

MIGRATIONS = Path(__file__).with_name('migrations')
TABLES = {'plans', 'plan_constraints', 'generated_itineraries', 'itinerary_stops',
          'source_metadata', 'schema_migrations'}


class MigrationError(Exception):
    """Do not print raw database errors or settings."""


def migration_files(directory=MIGRATIONS):
    files = sorted(directory.glob('*.sql'))
    if not files or any(not re.fullmatch(r'\d{4}_[a-z0-9_]+\.sql', p.name) for p in files):
        raise MigrationError('Invalid migration inventory')
    versions = [p.name[:4] for p in files]
    if len(set(versions)) != len(versions):
        raise MigrationError('Duplicate migration version')
    return [(p.name, sha256(p.read_bytes()).hexdigest(), p.read_text()) for p in files]


def applied_migrations(connection, files):
    exists = connection.execute("SELECT to_regnamespace('whereto') IS NOT NULL").fetchone()[0]
    if not exists:
        return {}
    if not connection.execute("SELECT to_regclass('whereto.schema_migrations') IS NOT NULL").fetchone()[0]:
        raise MigrationError('Existing schema has no migration ledger')
    applied = dict(connection.execute('SELECT version, checksum FROM whereto.schema_migrations').fetchall())
    expected = {name: checksum for name, checksum, _ in files}
    if not applied or any(expected.get(name) != checksum for name, checksum in applied.items()):
        raise MigrationError('Unknown or changed migration')
    if list(sorted(applied)) != [name for name, _, _ in files][:len(applied)]:
        raise MigrationError('Noncontiguous migration history')
    return applied


def migrate(connection, files=None):
    """Caller owns transaction. Repeated execution is a checksum-checked no-op."""
    files = migration_files() if files is None else files
    connection.execute("SELECT pg_advisory_xact_lock(4871048)")
    applied = applied_migrations(connection, files)
    count = 0
    for name, checksum, sql in files:
        if name not in applied:
            connection.execute(sql, prepare=False)
            connection.execute('INSERT INTO whereto.schema_migrations(version, checksum) VALUES (%s, %s)',
                               (name, checksum))
            count += 1
    return count


def verify_schema(connection):
    """Read-only catalog/privilege inspection; no fixture data or DDL."""
    files = migration_files()
    if len(applied_migrations(connection, files)) != len(files):
        raise MigrationError('Pending migration')
    rows = connection.execute("""
        SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity,
               pg_get_userbyid(c.relowner) = current_user
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='whereto' AND c.relkind='r'
    """).fetchall()
    if {r[0] for r in rows} != TABLES or any(not all(r[1:]) for r in rows):
        raise MigrationError('Unexpected tables, ownership or RLS')
    policies = connection.execute("SELECT tablename, policyname, roles FROM pg_policies WHERE schemaname='whereto'").fetchall()
    expected_policies = {'plans': 'private_plan', 'plan_constraints': 'private_constraints',
        'generated_itineraries': 'private_itineraries', 'itinerary_stops': 'private_stops', 'source_metadata': 'private_sources'}
    if {(r[0],r[1],tuple(r[2])) for r in policies} != {(t,p,('whereto_plan_runtime',)) for t,p in expected_policies.items()}:
        raise MigrationError('Unexpected access policy')
    # Inspect explicit ACLs too: RLS cannot compensate for schema/table grants.
    grants = connection.execute("""
        SELECT count(*) FROM (
          SELECT x.grantee FROM pg_namespace n,
            LATERAL aclexplode(coalesce(n.nspacl, acldefault('n', n.nspowner))) x
            WHERE n.nspname='whereto' AND x.grantee <> n.nspowner
          UNION ALL
          SELECT x.grantee FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace,
            LATERAL aclexplode(coalesce(c.relacl, acldefault('r', c.relowner))) x
            WHERE n.nspname='whereto' AND x.grantee <> c.relowner
        ) grants
    """).fetchone()[0]
    # Only the dedicated runtime role may have USAGE / SELECT / INSERT.
    unexpected = connection.execute("""
      SELECT count(*) FROM (
        SELECT x.grantee,x.privilege_type FROM pg_namespace n,
          LATERAL aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) x
          WHERE n.nspname='whereto' AND x.grantee<>n.nspowner
          AND (x.grantee<>'whereto_plan_runtime'::regrole OR x.privilege_type<>'USAGE' OR x.is_grantable)
        UNION ALL
        SELECT x.grantee,x.privilege_type FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace,
          LATERAL aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) x
          WHERE n.nspname='whereto' AND x.grantee<>c.relowner
          AND (x.grantee<>'whereto_plan_runtime'::regrole OR x.privilege_type NOT IN ('SELECT','INSERT')
            OR c.relname='schema_migrations' OR x.is_grantable)
      ) unexpected
    """).fetchone()[0]
    if unexpected or grants != 11:
        raise MigrationError('Unexpected grants')
    role = connection.execute("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolinherit FROM pg_roles WHERE rolname='whereto_plan_runtime'").fetchone()
    if role != (False,False,False,False,False):
        raise MigrationError('Unsafe runtime role')
    if connection.execute("SELECT count(*) FROM pg_auth_members WHERE member='whereto_plan_runtime'::regrole").fetchone()[0]:
        raise MigrationError('Runtime role must not belong to other roles')
    for role in ('anon', 'authenticated', 'service_role'):
        if connection.execute("SELECT has_schema_privilege(%s, 'whereto', 'USAGE')", (role,)).fetchone()[0]:
            raise MigrationError('API role has schema access')
        for table in sorted(TABLES):
            if connection.execute("SELECT has_table_privilege(%s, %s, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",
                                  (role, 'whereto.' + table)).fetchone()[0]:
                raise MigrationError('API role has table access')
    return sorted(TABLES)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Controlled PostgreSQL schema migration')
    parser.add_argument('action', choices=('check', 'apply', 'verify'))
    args = parser.parse_args(argv)
    try:
        settings = connection_settings(os.environ)
        settings['application_name'] = 'whereto-schema-admin'
        with psycopg.connect(**settings) as connection:
            if not connection.pgconn.ssl_in_use:
                raise MigrationError('TLS required')
            connection.read_only = args.action == 'verify'
            connection.execute("SET LOCAL statement_timeout = '15s'")
            connection.execute("SET LOCAL lock_timeout = '5s'")
            if args.action != 'verify':
                migrate(connection)
            verify_schema(connection)
            if args.action == 'apply':
                connection.commit()
            else:
                connection.rollback()
    except (DatabaseCheckError, MigrationError, psycopg.Error, OSError, ValueError):
        print('Schema operation failed; completion is unconfirmed. Run verify before retrying; check configuration, history and permissions privately. See docs/database-schema.md.')
        return 1
    print({'check': 'Schema rehearsal passed; transaction rolled back.',
           'apply': 'Schema migration applied or already current; verification passed.',
           'verify': 'Read-only hosted schema, ledger, ownership, grants and RLS verification passed.'}[args.action])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
