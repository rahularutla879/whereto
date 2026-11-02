"""Task 50 regressions. Invented fixtures; providers never contacted."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import os
import secrets
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from pydantic import ValidationError
from backend.saved_plans import (database, digest, reopen, save, OpenRequest,
    SaveRequest, SavedDocument, PersistenceError, Receipts, write_document, read_document)
from backend.test_saved_plans import request_for
from backend.persistence_config import runtime_settings
from backend.database_check import connection_settings


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.registry = Receipts()
        self.request = request_for(self.registry)
        self.document = self.registry.select(self.request)

    def test_untrusted_fields_injection_and_token_substitution(self):
        for change in ({'accessToken': "'; DROP TABLE whereto.plans;--"}, {'plan_id': str(uuid4())},
                       {'owner': 'administrator'}, {'candidateIds': ['x'] * 4}):
            with self.assertRaises(ValidationError):
                SaveRequest.model_validate(self.request.model_dump() | change)
        for change in ({'accessToken': secrets.token_urlsafe(32)}, {'selectedId': "' OR 1=1--"}):
            with self.assertRaises(PersistenceError):
                self.registry.select(self.request.model_copy(update=change))

    def test_persisted_constraints_and_provider_references(self):
        for changes in ({'date': '2026-02-30'}, {'startTime': 900, 'endTime': 800},
                        {'travel': -1}, {'transport': 'flying'}, {'activities': ['unsupported']}):
            value = self.document.model_dump(mode='json')
            value['constraints'].update(changes)
            with self.assertRaises(ValidationError): SavedDocument.model_validate(value)
        from backend.saved_plans import SavedStop
        stop = self.document.itineraries[0].stops[0].model_dump()
        for reference in ('../other', 'place?key=SECRET', 'place/another', 'bad id', 'x\n'):
            with self.assertRaises(ValidationError):
                SavedStop.model_validate(stop | {'provider': 'google_places', 'reference': reference})

    def test_duplicate_concurrent_receipt_selection(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.registry.select(self.request), range(12)))
        self.assertTrue(all(value == self.document for value in results))

    def test_expired_receipt_never_connects(self):
        with patch('backend.saved_plans.receipts', self.registry), patch('backend.saved_plans.monotonic', return_value=10**15), patch('psycopg.connect') as connect:
            with self.assertRaises(PersistenceError): save(self.request)
            connect.assert_not_called()

    def test_connection_interrupt_and_uncertain_commit_no_retry_cleanup(self):
        import backend.saved_plans as module
        for phase in ('connect', 'query', 'commit'):
            manager = MagicMock()
            conn = manager.__enter__.return_value
            conn.execute.return_value.fetchone.return_value = {'role': 'whereto_plan_runtime'}
            error = psycopg.OperationalError('PRIVATE_PASSWORD PRIVATE_TOKEN')
            if phase == 'query': conn.execute.side_effect = error
            if phase == 'commit': manager.__exit__.side_effect = error
            with patch.object(module, 'connection_settings', return_value={'user': 'whereto_plan_runtime.fixture'}), patch('psycopg.connect', side_effect=error if phase=='connect' else None, return_value=manager) as connect:
                with self.assertRaises(PersistenceError) as caught:
                    with database(self.request.accessToken): pass
                self.assertEqual(caught.exception.code, 'database_connection_failed')
                self.assertNotIn('PRIVATE', str(caught.exception))
                self.assertEqual(connect.call_count, 1)
                if phase != 'connect': manager.__exit__.assert_called_once()
            # Every failure must release all four admission slots.
            for _ in range(4): self.assertTrue(module.connections.acquire(blocking=False))
            for _ in range(4): module.connections.release()

    def test_corrupt_record_reopen_and_refresh_fail_closed(self):
        @contextmanager
        def connection(*args, **kwargs): yield object()
        from backend.saved_refresh import RefreshSessions, RefreshRequest
        with patch('backend.saved_plans.database', connection), patch('backend.saved_plans.read_document', side_effect=ValidationError.from_exception_data('Stored', [])), patch('backend.saved_refresh.fetch_saved_details') as provider:
            for action in (lambda: reopen(OpenRequest(accessToken=self.request.accessToken)),
                           lambda: RefreshSessions().refresh(RefreshRequest(accessToken=self.request.accessToken, candidateId=self.document.selectedId, refreshId=uuid4()), object())):
                with self.assertRaises(PersistenceError) as caught: action()
                self.assertEqual(caught.exception.status,404)
            provider.assert_not_called()

    def test_valid_save_and_reopen_use_distinct_transactions(self):
        calls = []
        @contextmanager
        def connection(token, readonly=False):
            calls.append((token, readonly))
            yield object()
        with patch('backend.saved_plans.receipts', self.registry), patch('backend.saved_plans.database', connection), patch('backend.saved_plans.write_document') as write, patch('backend.saved_plans.read_document', return_value={'saved':True}) as read:
            self.assertEqual(save(self.request), {'saved':True})
            self.assertEqual(reopen(OpenRequest(accessToken=self.request.accessToken)), {'saved':True})
            self.assertEqual([readonly for _,readonly in calls], [False,True])
            write.assert_called_once(); read.assert_called_once()

    def test_missing_invalid_expired_records_stop_before_child_queries(self):
        for token in (self.request.accessToken, secrets.token_urlsafe(32)):
            connection = MagicMock()
            connection.execute.return_value.fetchone.return_value = None
            with self.assertRaises(PersistenceError) as caught: read_document(connection,token)
            self.assertEqual(caught.exception.status,404)
            connection.execute.assert_called_once()
            query, parameters = connection.execute.call_args.args
            self.assertIn('access_expires_at>now()',query)
            self.assertNotIn(token,query)
            self.assertEqual(parameters,(digest(token),))

    def test_duplicate_submission_does_not_insert_and_changed_selection_denied(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = {'save_fingerprint':digest(self.document.model_dump_json())}
        with patch('backend.saved_plans.insert') as insert:
            write_document(conn,self.document,self.request.accessToken)
            insert.assert_not_called()
            changed=self.document.model_copy(update={'selectedId':self.document.itineraries[0].candidateId})
            with self.assertRaises(PersistenceError): write_document(conn,changed,self.request.accessToken)
            insert.assert_not_called()

    def test_restricted_role_denial_is_safe_and_transaction_rolls_back(self):
        manager=MagicMock(); conn=manager.__enter__.return_value
        conn.execute.return_value.fetchone.return_value={'role':'whereto_plan_runtime'}
        with patch('backend.saved_plans.connection_settings',return_value={'user':'whereto_plan_runtime.fixture'}), patch('psycopg.connect',return_value=manager):
            with self.assertRaises(PersistenceError) as caught:
                with database(self.request.accessToken) as connection:
                    raise psycopg.errors.InsufficientPrivilege('PRIVATE table and credentials')
            self.assertEqual(caught.exception.code,'database_access_denied')
            self.assertNotIn('PRIVATE',str(caught.exception))
            self.assertIs(manager.__exit__.call_args.args[0],psycopg.errors.InsufficientPrivilege)

    def test_four_active_connections_bound_fifth_request_without_connecting(self):
        import backend.saved_plans as module
        from threading import Barrier
        barrier=Barrier(5); release=Barrier(5)
        @contextmanager
        def hold():
            manager=MagicMock(); conn=manager.__enter__.return_value
            conn.execute.return_value.fetchone.return_value={'role':'whereto_plan_runtime'}
            yield manager
        def worker(_):
            with database(self.request.accessToken): barrier.wait(timeout=5); release.wait(timeout=5)
        with hold() as manager, patch.object(module,'connection_settings',return_value={'user':'whereto_plan_runtime.fixture'}), patch('psycopg.connect',return_value=manager) as connect:
            with ThreadPoolExecutor(max_workers=4) as pool:
                pending=[pool.submit(worker,i) for i in range(4)]
                barrier.wait(timeout=5)
                try:
                    with self.assertRaises(PersistenceError):
                        with database(self.request.accessToken): pass
                    self.assertEqual(connect.call_count,4)
                finally: release.wait(timeout=5)
                for future in pending: future.result()

    def test_secret_redaction_in_evidence(self):
        from backend.failures import evidence
        with self.assertLogs('whereto.failures') as logs:
            evidence('database_connection_failed','reopen',exception=psycopg.OperationalError('PRIVATE_PASSWORD PRIVATE_TOKEN'))
        self.assertNotIn('PRIVATE', str(logs.output))

    def test_refresh_rejects_arbitrary_ids_and_unselected_option(self):
        from backend.saved_refresh import RefreshSessions, RefreshRequest, fetch_saved_details
        request = RefreshRequest(accessToken=self.request.accessToken, candidateId='other', refreshId=uuid4())
        with patch('backend.saved_refresh.reopen', return_value=self.document.model_dump() | {'dataMode':'real'}), patch('backend.saved_refresh.fetch_saved_details') as provider:
            with self.assertRaises(PersistenceError): RefreshSessions().refresh(request, object())
            provider.assert_not_called()
        with self.assertRaises(ValidationError):
            RefreshRequest.model_validate(request.model_dump() | {'placeIds':['arbitrary']})
        with patch('backend.places_transport.access_token') as auth:
            with self.assertRaises(PersistenceError): fetch_saved_details('../arbitrary')
            auth.assert_not_called()


@unittest.skipUnless(os.environ.get('WHERETO_DB_SCHEMA_TESTS')=='1', 'Opt-in hosted Task 50 tests')
class HostedSecurityTests(unittest.TestCase):
    def setUp(self):
        self.admin = psycopg.connect(**connection_settings(os.environ), autocommit=True)
        self.addCleanup(self.admin.close)
        self.registry = Receipts(); self.request = request_for(self.registry)
        self.document = self.registry.select(self.request)
        self.hashes = {digest(self.request.accessToken)}
        self.addCleanup(self.cleanup_records)

    def cleanup_records(self):
        # Exact test-generated capabilities only; committed deletion verified.
        for key in self.hashes:
            self.admin.execute('DELETE FROM whereto.plans WHERE access_hash=%s',(key,))
            self.assertEqual(self.admin.execute('SELECT count(*) FROM whereto.plans WHERE access_hash=%s',(key,)).fetchone()[0],0)

    def test_restricted_authenticated_tls_and_role_boundaries(self):
        with database(self.request.accessToken) as conn:
            self.assertTrue(conn.pgconn.ssl_in_use)
            # Supavisor may replace startup application_name; do not infer identity from it.
            self.assertEqual(conn.execute('SELECT current_user AS role').fetchone()['role'],'whereto_plan_runtime')
            flags=conn.execute("SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolinherit FROM pg_roles WHERE rolname=current_user").fetchone()
            self.assertTrue(all(value is False for value in flags.values()))
            self.assertEqual(conn.execute("SELECT count(*) AS n FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user)").fetchone()['n'],0)
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM whereto.plans').fetchone()['n'],0)
            for query in ('SELECT * FROM whereto.schema_migrations','ALTER TABLE whereto.plans DISABLE ROW LEVEL SECURITY','CREATE ROLE task50_forbidden','DELETE FROM whereto.plans','UPDATE whereto.plans SET selected_option=0'):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with conn.transaction(): conn.execute(query)
            # PostgreSQL GRANT by a nonowner can warn/no-op rather than raise.
            # Roll the probe back regardless of its result.
            class RollbackProbe(Exception): pass
            with self.assertRaises(RollbackProbe):
                with conn.transaction():
                    conn.execute('GRANT SELECT ON whereto.plans TO PUBLIC')
                    self.assertFalse(conn.execute("SELECT has_table_privilege('anon','whereto.plans','SELECT') AS allowed").fetchone()['allowed'])
                    raise RollbackProbe()

    def test_concurrent_idempotent_writes_reads_and_restart(self):
        with patch('backend.saved_plans.receipts', self.registry):
            with ThreadPoolExecutor(max_workers=3) as pool:
                self.assertTrue(all(v=={'saved':True} for v in pool.map(lambda _:save(self.request),range(3))))
        self.assertEqual(self.admin.execute('SELECT count(*) FROM whereto.plans WHERE access_hash=%s',(digest(self.request.accessToken),)).fetchone()[0],1)
        with ThreadPoolExecutor(max_workers=3) as pool:
            docs=list(pool.map(lambda _:reopen(OpenRequest(accessToken=self.request.accessToken)),range(6)))
        self.assertTrue(all(v['selectedId']==self.document.selectedId for v in docs))
        # Fresh interpreter: no receipts or Python connection state survive restart.
        import subprocess,sys
        code="import os; from backend.saved_plans import reopen,OpenRequest; assert reopen(OpenRequest(accessToken=os.environ['TASK50_TOKEN']))['saved']"
        result=subprocess.run([sys.executable,'-c',code],env=dict(os.environ,TASK50_TOKEN=self.request.accessToken),capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,'Fresh-process reopen failed (output withheld)')

    def test_actual_connection_interruption_then_fresh_reopen(self):
        with database(self.request.accessToken) as conn: write_document(conn,self.document,self.request.accessToken)
        with self.assertRaises(PersistenceError) as caught:
            with database(self.request.accessToken,readonly=True) as conn:
                # Pooler protocol PID is synthetic; target only this actual test session.
                pid=conn.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid']
                self.assertTrue(self.admin.execute('SELECT pg_terminate_backend(%s)',(pid,)).fetchone()[0])
                read_document(conn,self.request.accessToken)
        self.assertEqual(caught.exception.code,'database_connection_failed')
        self.assertTrue(reopen(OpenRequest(accessToken=self.request.accessToken))['saved'])

    def test_two_capabilities_and_sql_injection_stay_isolated(self):
        other=request_for(self.registry); self.hashes.add(digest(other.accessToken))
        for request in (self.request,other):
            with database(request.accessToken) as conn: write_document(conn,self.registry.select(request),request.accessToken)
        with database(self.request.accessToken,readonly=True) as conn:
            with self.assertRaises(PersistenceError): read_document(conn,other.accessToken)
            self.assertEqual(conn.execute("SELECT count(*) AS n FROM whereto.generated_itineraries WHERE candidate_id=%s",("' OR 1=1--",)).fetchone()['n'],0)
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM whereto.plans').fetchone()['n'],1)
        self.admin.execute("UPDATE whereto.plans SET access_expires_at=now()-interval '1 second' WHERE access_hash=%s",(digest(self.request.accessToken),))
        with self.assertRaises(PersistenceError) as caught: reopen(OpenRequest(accessToken=self.request.accessToken))
        self.assertEqual(caught.exception.status,404)

    def test_runtime_write_failure_rolls_back_committed_state(self):
        import backend.saved_plans as module
        original=module.insert
        def fail(conn,table,values):
            if table=='source_metadata': raise psycopg.IntegrityError('Invented interruption')
            original(conn,table,values)
        with patch.object(module,'insert',side_effect=fail), self.assertRaises(PersistenceError):
            with database(self.request.accessToken) as conn: write_document(conn,self.document,self.request.accessToken)
        self.assertEqual(self.admin.execute('SELECT count(*) FROM whereto.plans WHERE access_hash=%s',(digest(self.request.accessToken),)).fetchone()[0],0)

    def test_existing_nonexpired_documents_compatible_readonly(self):
        # Never disclose existing contents or mutate owner records.
        keys=self.admin.execute('SELECT access_hash FROM whereto.plans WHERE access_hash IS NOT NULL AND access_expires_at>now() LIMIT 20').fetchall()
        with psycopg.connect(**runtime_settings(os.environ), row_factory=dict_row) as conn:
            conn.read_only=True
            for (key,) in keys:
                conn.execute("SELECT set_config('whereto.access_hash',%s,true)",(key,))
                with patch('backend.saved_plans.digest',return_value=key):
                    self.assertTrue(read_document(conn,'withheld')['saved'])
