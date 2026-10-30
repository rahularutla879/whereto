"""Offline checks only: these tests never contact Supabase."""

from contextlib import redirect_stdout
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import call, patch

import psycopg

from backend.database_check import DatabaseCheckError, connection_settings, main, verify_database


class DatabaseCheckTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        cert = Path(self.directory.name) / "ca.crt"
        cert.write_text("test certificate placeholder")
        self.env = {"WHERETO_DB_HOST": "aws-0-us-east-1.pooler.supabase.com",
                    "WHERETO_DB_NAME": "postgres", "WHERETO_DB_USER": "postgres.example",
                    "WHERETO_DB_PASSWORD": "secret-$-quote-'", "WHERETO_DB_SSLROOTCERT": str(cert)}

    @patch("backend.database_check.psycopg.connect")
    def test_invalid_settings_never_connect(self, connect):
        cases = [{}]
        cases.extend({**self.env, key: ""} for key in self.env)
        cases.extend({**self.env, **change} for change in (
            {"WHERETO_DB_HOST": "localhost"}, {"WHERETO_DB_PORT": "6543"},
            {"WHERETO_DB_SSLROOTCERT": "/missing/ca.crt"},
            {"WHERETO_DB_HOST": "postgres://user:secret@host"}))
        for env in cases:
            with self.subTest(keys=list(env)), self.assertRaises(DatabaseCheckError):
                verify_database(env)
        connect.assert_not_called()

    def test_tls_and_timeouts_cannot_be_downgraded(self):
        settings = connection_settings({**self.env, "PGSSLMODE": "disable"})
        self.assertEqual(settings["sslmode"], "verify-full")
        self.assertEqual(settings["password"], self.env["WHERETO_DB_PASSWORD"])
        self.assertEqual(settings["connect_timeout"], 10)
        self.assertEqual(settings["options"], "")

    @patch("backend.database_check.socket.getaddrinfo", side_effect=OSError("sensitive"))
    @patch("backend.database_check.psycopg.connect")
    def test_dns_failure_stops_before_authentication(self, connect, dns):
        with self.assertRaisesRegex(DatabaseCheckError, "DNS resolution failed"):
            verify_database(self.env)
        connect.assert_not_called()

    @patch("backend.database_check.socket.getaddrinfo")
    @patch("backend.database_check.psycopg.connect")
    def test_readonly_success_closes_connection(self, connect, dns):
        connection = connect.return_value.__enter__.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1, "on")
        verify_database(self.env)
        self.assertTrue(connection.read_only)
        self.assertEqual(cursor.execute.call_args_list, [
            call("SET LOCAL statement_timeout = '5s'"),
            call("SELECT 1, current_setting('transaction_read_only')")])
        connection.rollback.assert_called_once()
        connect.return_value.__exit__.assert_called_once()

    @patch("backend.database_check.socket.getaddrinfo")
    @patch("backend.database_check.psycopg.connect")
    def test_failed_tls_or_query_closes_connection(self, connect, dns):
        connection = connect.return_value.__enter__.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        for tls, row in ((False, (1, "on")), (True, (1, "off")), (True, None)):
            with self.subTest(tls=tls, row=row):
                connect.return_value.__exit__.reset_mock()
                connection.pgconn.ssl_in_use = tls
                cursor.fetchone.return_value = row
                with self.assertRaises(DatabaseCheckError):
                    verify_database(self.env)
                connect.return_value.__exit__.assert_called_once()

    @patch("backend.database_check.socket.getaddrinfo")
    @patch("backend.database_check.psycopg.connect")
    def test_driver_errors_do_not_leak_secrets(self, connect, dns):
        connect.side_effect = psycopg.OperationalError(self.env["WHERETO_DB_PASSWORD"])
        output = io.StringIO()
        with patch.dict("os.environ", self.env, clear=True), redirect_stdout(output):
            self.assertEqual(main(), 1)
        self.assertNotIn(self.env["WHERETO_DB_PASSWORD"], output.getvalue())
        self.assertNotIn(self.env["WHERETO_DB_HOST"], output.getvalue())

    def test_missing_configuration_cli_is_safe(self):
        with patch.dict("os.environ", {}, clear=True), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(), 1)
        self.assertIn("Database check failed", output.getvalue())
