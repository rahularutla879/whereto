"""Opt-in read-only PostgreSQL check; never imported by application startup."""

import os
from pathlib import Path
import re
import socket
from collections.abc import Mapping

import psycopg


class DatabaseCheckError(Exception):
    """Only fixed, credential-free messages may cross this boundary."""


def connection_settings(env: Mapping[str, str]) -> dict:
    names = ("HOST", "NAME", "USER", "PASSWORD", "SSLROOTCERT")
    if any(not env.get("WHERETO_DB_" + name, "").strip() for name in names):
        raise DatabaseCheckError("Missing database settings. See backend/.env.example.")
    host = env["WHERETO_DB_HOST"].strip()
    # Task 47 intentionally supports only the shared Supabase session pooler.
    if not re.fullmatch(r"[a-z0-9-]+\.pooler\.supabase\.com", host):
        raise DatabaseCheckError("Use the Supabase shared session-pooler hostname.")
    if env.get("WHERETO_DB_PORT", "5432") != "5432":
        raise DatabaseCheckError("Session-pooler port must be 5432.")
    certificate = Path(env["WHERETO_DB_SSLROOTCERT"]).expanduser()
    if not certificate.is_file():
        raise DatabaseCheckError("Database CA certificate file is missing.")
    return dict(host=host, port=5432, dbname=env["WHERETO_DB_NAME"],
                user=env["WHERETO_DB_USER"], password=env["WHERETO_DB_PASSWORD"],
                sslmode="verify-full", sslrootcert=str(certificate),
                connect_timeout=10, application_name="whereto-readonly-check",
                options="")


def verify_database(env: Mapping[str, str]) -> None:
    settings = connection_settings(env)
    try:
        socket.getaddrinfo(settings["host"], settings["port"], type=socket.SOCK_STREAM)
    except OSError:
        raise DatabaseCheckError("Database endpoint DNS resolution failed.") from None
    try:
        with psycopg.connect(**settings) as connection:
            if not connection.pgconn.ssl_in_use:
                raise DatabaseCheckError("Database connection did not use TLS.")
            connection.read_only = True
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = '5s'")
                cursor.execute("SELECT 1, current_setting('transaction_read_only')")
                if cursor.fetchone() != (1, "on"):
                    raise DatabaseCheckError("Read-only database verification failed.")
            # Roll back even the read-only transaction before closing the session.
            connection.rollback()
    except psycopg.Error:
        # Driver errors can include usernames, hosts and arbitrary server text.
        raise DatabaseCheckError(
            "Database connection/query failed. Check project readiness, network, credentials and CA certificate."
        ) from None


def main() -> int:
    try:
        verify_database(os.environ)
    except (DatabaseCheckError, OSError, ValueError):
        # Do not print raw settings, exception text, DSNs or tracebacks.
        print("Database check failed. Verify required settings, session-pooler endpoint, network, credentials and CA certificate; see docs/database-setup.md.")
        return 1
    print("Database check passed: DNS, authenticated SELECT, read-only transaction and verified client-to-pooler TLS; connection closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
