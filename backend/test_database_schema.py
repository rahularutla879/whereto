"""Offline runner tests + explicitly opt-in real PostgreSQL rollback fixtures.

WHERETO_DB_SCHEMA_TESTS=1 requires the owner's trusted private DB settings.
Every hosted test rolls back, including rehearsal DDL on a fresh project.
"""
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from backend.database_check import connection_settings
from backend.database_migrate import (MigrationError, TABLES, main, migrate,
                                      migration_files, verify_schema)
from backend.models import PlanningRequest
from backend.ranking import recommend_plans


class MigrationOfflineTests(unittest.TestCase):
    def test_inventory_is_stable_and_no_destructive_sql(self):
        files = migration_files()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0][0], '0001_initial_planning.sql')
        self.assertEqual(len(files[0][1]), 64)
        sql = files[0][2].upper()
        for forbidden in ('DROP ', 'TRUNCATE ', 'CREATE ROLE', 'GRANT ALL', 'SECURITY DEFINER'):
            self.assertNotIn(forbidden, sql)
        self.assertEqual(files, migration_files())

    def test_bad_or_duplicate_versions_fail(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)
            with self.assertRaises(MigrationError):
                migration_files(path)
            (path / 'bad.sql').write_text('SELECT 1')
            with self.assertRaises(MigrationError):
                migration_files(path)
            (path / 'bad.sql').unlink()
            for name in ('0001_one.sql', '0001_two.sql'):
                (path / name).write_text('SELECT 1')
            with self.assertRaises(MigrationError):
                migration_files(path)

    def test_missing_configuration_never_connects(self):
        with patch.dict(os.environ, {}, clear=True), patch('psycopg.connect') as connect:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(['apply']), 1)
            connect.assert_not_called()

    def test_cli_redacts_driver_errors(self):
        with patch('backend.database_migrate.connection_settings', return_value={}), \
             patch('psycopg.connect', side_effect=psycopg.OperationalError('private-password')):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(['apply']), 1)
            self.assertNotIn('private-password', output.getvalue())

    def test_mock_planning_without_database(self):
        with patch.dict(os.environ, {}, clear=True), patch('psycopg.connect', side_effect=AssertionError('No DB')):
            result = recommend_plans(PlanningRequest(activities=['coffee', 'museum'], date='2026-11-07'))
            self.assertTrue(result.plans or result.provisionalPlans)
            self.assertEqual(result.dataMode, 'mock')


@unittest.skipUnless(os.environ.get('WHERETO_DB_SCHEMA_TESTS') == '1', 'Opt-in hosted rollback tests')
class HostedSchemaTests(unittest.TestCase):
    def setUp(self):
        self.connection = psycopg.connect(**connection_settings(os.environ), autocommit=True)
        self.addCleanup(self.connection.close)
        self.addCleanup(self.connection.rollback)
        self.connection.execute('BEGIN')
        # autocommit=True connections need explicit SQL ROLLBACK.
        self.addCleanup(lambda: self.connection.execute('ROLLBACK'))
        self.connection.execute("SET LOCAL statement_timeout = '15s'")
        self.connection.execute("SET LOCAL lock_timeout = '5s'")
        self.assertTrue(self.connection.pgconn.ssl_in_use)
        migrate(self.connection)
        self.plan = self.connection.execute("INSERT INTO whereto.plans(data_mode) VALUES ('mock') RETURNING id").fetchone()[0]
        self.itinerary = self.connection.execute("""INSERT INTO whereto.generated_itineraries
            (plan_id, option_position, candidate_id, feasibility)
            VALUES (%s, 0, 'candidate-fixture', 'provisional') RETURNING id""", (self.plan,)).fetchone()[0]

    def invalid(self, sql, params=(), error=psycopg.IntegrityError):
        with self.assertRaises(error):
            with self.connection.transaction():
                self.connection.execute(sql, params)

    def add_stop(self, position=0, activity='coffee'):
        return self.connection.execute("""INSERT INTO whereto.itinerary_stops
            (itinerary_id, position, activity) VALUES (%s,%s,%s) RETURNING id""",
            (self.itinerary, position, activity)).fetchone()[0]

    def test_actual_catalog_security_and_columns(self):
        self.assertEqual(set(verify_schema(self.connection)), TABLES)
        columns = self.connection.execute("""SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns WHERE table_schema='whereto'""").fetchall()
        by_table = {table: {c[1] for c in columns if c[0] == table} for table in TABLES}
        for table, required in {
            'plans': {'id','created_at','updated_at','original_request','data_mode','model_version'},
            'plan_constraints': {'plan_id','activities','outing_date','first_travel_mode','require_wheelchair_access','between_travel_value'},
            'generated_itineraries': {'id','plan_id','candidate_id','option_position','ranking_score','generated_at'},
            'itinerary_stops': {'id','itinerary_id','position','activity','timing_basis','duration_minutes'},
            'source_metadata': {'id','stop_id','provider','external_id','observed_at','storage_policy'},
        }.items():
            self.assertTrue(required <= by_table[table])
        forbidden = {'password','email','user_id','latitude','longitude','raw_payload','address','rating','maps_url','budget','people'}
        self.assertFalse(forbidden & {c[1] for c in columns})
        for table, column, dtype, nullable in columns:
            if column in ('id','plan_id','stop_id','itinerary_id'):
                self.assertEqual((dtype, nullable), ('uuid','NO'))
        keys = self.connection.execute("""SELECT contype, count(*) FROM pg_constraint
            WHERE connamespace='whereto'::regnamespace GROUP BY contype""").fetchall()
        self.assertEqual(dict(keys)['p'], 6)
        self.assertEqual(dict(keys)['f'], 4)
        self.assertEqual(dict(keys)['u'], 4)
        self.assertGreater(dict(keys)['c'], 35)
        indexes = {r[0] for r in self.connection.execute("SELECT indexname FROM pg_indexes WHERE schemaname='whereto'")}
        self.assertTrue({'plans_created_at_idx','source_metadata_lookup_idx',
                         'generated_itineraries_plan_id_option_position_key',
                         'itinerary_stops_itinerary_id_position_key'} <= indexes)

    def test_ordering_uniqueness_and_many_options(self):
        for position in (2,0,1):
            self.add_stop(position)
        self.assertEqual([r[0] for r in self.connection.execute(
            'SELECT position FROM whereto.itinerary_stops WHERE itinerary_id=%s ORDER BY position', (self.itinerary,))], [0,1,2])
        self.invalid('INSERT INTO whereto.itinerary_stops(itinerary_id,position,activity) VALUES (%s,0,\'coffee\')', (self.itinerary,))
        self.invalid('INSERT INTO whereto.itinerary_stops(itinerary_id,position,activity) VALUES (%s,-1,\'coffee\')', (self.itinerary,))
        self.connection.execute("""INSERT INTO whereto.generated_itineraries
            (plan_id,option_position,candidate_id,feasibility) VALUES (%s,1,'candidate-other','provisional')""", (self.plan,))
        for position, candidate in ((0,'candidate-new'), (2,'candidate-fixture')):
            self.invalid("""INSERT INTO whereto.generated_itineraries(plan_id,option_position,candidate_id,feasibility)
                VALUES (%s,%s,%s,'confirmed')""", (self.plan,position,candidate))

    def test_foreign_keys_and_cascade(self):
        stop = self.add_stop()
        self.connection.execute("INSERT INTO whereto.source_metadata(stop_id,reference_kind,provider) VALUES (%s,'incoming_route','google_routes')", (stop,))
        self.invalid("INSERT INTO whereto.itinerary_stops(itinerary_id,position,activity) VALUES (%s,0,'coffee')", (uuid4(),))
        self.invalid("INSERT INTO whereto.source_metadata(stop_id,reference_kind,provider) VALUES (%s,'venue','mock')", (uuid4(),))
        self.invalid("INSERT INTO whereto.plan_constraints(plan_id,outing_date,location_text,activities) VALUES (%s,'2026-11-07','Baltimore',ARRAY['coffee'])", (uuid4(),))
        self.connection.execute('DELETE FROM whereto.plans WHERE id=%s', (self.plan,))
        for table, column, value in (('generated_itineraries','id',self.itinerary), ('itinerary_stops','id',stop), ('source_metadata','stop_id',stop)):
            self.assertEqual(self.connection.execute(f'SELECT count(*) FROM whereto.{table} WHERE {column}=%s', (value,)).fetchone()[0], 0)

    def test_constraints_match_current_request(self):
        request = PlanningRequest(activities=['coffee','custom:pottery','coffee'],
            activityIntents={'custom:pottery':'pottery'}, date='2026-11-07', transport='driving',
            firstTravel={'value':5.0,'unit':'minutes','mode':'flexible'}, requireWheelchairAccess=True)
        self.connection.execute("""INSERT INTO whereto.plan_constraints
            (plan_id,outing_date,location_text,activities,activity_intents,transport,
             first_travel_value,first_travel_unit,first_travel_mode,require_wheelchair_access)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (self.plan,request.date,request.location,
            [a.value for a in request.activities],Jsonb(request.activityIntents),request.transport.value,
            request.firstTravel.value,request.firstTravel.unit,request.firstTravel.mode,request.requireWheelchairAccess))
        row = self.connection.execute('SELECT activities,first_travel_mode,require_wheelchair_access FROM whereto.plan_constraints WHERE plan_id=%s', (self.plan,)).fetchone()
        self.assertEqual(row, (['coffee','custom:pottery','coffee'],'flexible',True))
        for change in ("end_minute=0", "first_travel_value=-1", "first_travel_unit='meters'",
                       "first_travel_mode=NULL", "activities='{}'", "activity_intents='[]'",
                       "transport='flying'", "excluded_regions=ARRAY['XX']", "dinner_stops=ARRAY[3]"):
            self.invalid('UPDATE whereto.plan_constraints SET ' + change + ' WHERE plan_id=%s', (self.plan,))
        self.invalid("INSERT INTO whereto.plan_constraints(plan_id,outing_date,location_text,activities) VALUES (%s,'2026-11-07','Baltimore',ARRAY['coffee'])", (self.plan,))
        self.connection.execute('DELETE FROM whereto.plans WHERE id=%s', (self.plan,))
        self.assertEqual(self.connection.execute('SELECT count(*) FROM whereto.plan_constraints WHERE plan_id=%s', (self.plan,)).fetchone()[0], 0)

    def test_provider_identifiers_only(self):
        stop = self.add_stop()
        self.connection.execute("""INSERT INTO whereto.source_metadata
            (stop_id,reference_kind,provider,external_id,evidence_status)
            VALUES (%s,'venue','google_places','ChIJ_fixture_only','reported')""", (stop,))
        self.connection.execute("INSERT INTO whereto.source_metadata(stop_id,reference_kind,provider) VALUES (%s,'incoming_route','other_provider')", (stop,))
        for number, (provider, kind, identity) in enumerate((('google_routes','incoming_route','route-content'),
                                         ('unreviewed','venue','unapproved-id'),
                                         ('google_places','venue',None),
                                         ('google_places','venue','bad id'))):
            self.invalid("INSERT INTO whereto.source_metadata(stop_id,reference_kind,provider,external_id) VALUES (%s,%s,%s,%s)", (self.add_stop(position=number+10, activity='museum'),kind,provider,identity))
        self.invalid("UPDATE whereto.source_metadata SET storage_policy='permanent_payload' WHERE stop_id=%s", (stop,))
        self.invalid("INSERT INTO whereto.source_metadata(stop_id,reference_kind,provider,external_id) VALUES (%s,'venue','google_places','ChIJ_other')", (stop,))

    def test_stop_times_and_ranking_bounds(self):
        stop = self.add_stop()
        self.invalid('UPDATE whereto.itinerary_stops SET duration_minutes=30 WHERE id=%s', (stop,))
        self.connection.execute("UPDATE whereto.itinerary_stops SET timing_basis='fictional',start_minute=600,end_minute=630,duration_minutes=30 WHERE id=%s", (stop,))
        for change in ('end_minute=590','duration_minutes=0','duration_minutes=31'):
            self.invalid('UPDATE whereto.itinerary_stops SET ' + change + ' WHERE id=%s', (stop,))
        for score in (-0.1, 1.1, float('nan'), float('inf')):
            self.invalid('UPDATE whereto.generated_itineraries SET ranking_score=%s WHERE id=%s', (score,self.itinerary))

    def test_current_mock_candidate_references(self):
        result = recommend_plans(PlanningRequest(activities=['coffee','museum'], date='2026-11-07'))
        ranked = (result.plans + result.provisionalPlans)[0]
        self.connection.execute('UPDATE whereto.generated_itineraries SET candidate_id=%s, ranking_score=%s WHERE id=%s',
                                (ranked.candidate.id,ranked.score,self.itinerary))
        ids = []
        for index, planned in enumerate(ranked.stops):
            stop = self.add_stop(index,planned.venue.activity.value)
            self.connection.execute("INSERT INTO whereto.source_metadata(stop_id,reference_kind,provider,external_id,evidence_status) VALUES (%s,'venue','mock',%s,'fictional')", (stop,planned.venue.id))
            ids.append(planned.venue.id)
        stored = self.connection.execute("""SELECT m.external_id FROM whereto.itinerary_stops s JOIN whereto.source_metadata m ON m.stop_id=s.id
            WHERE s.itinerary_id=%s ORDER BY s.position""", (self.itinerary,)).fetchall()
        self.assertEqual([r[0] for r in stored], ids)

    def test_repeated_migration_and_checksum_drift(self):
        self.assertEqual(migrate(self.connection), 0)
        files = migration_files()
        changed = [(name,'0'*64,sql) for name,_,sql in files]
        with self.assertRaises(MigrationError):
            migrate(self.connection,changed)
        with self.assertRaises(MigrationError):
            migrate(self.connection,[])
        self.assertEqual(migrate(self.connection), 0)

    def test_failed_migration_is_atomic(self):
        files = migration_files() + [('0002_rollback_probe.sql', '1'*64,
            'CREATE TABLE whereto.rollback_probe(id integer); SELECT 1/0;')]
        with self.assertRaises(psycopg.errors.DivisionByZero):
            with self.connection.transaction():
                migrate(self.connection, files)
        self.assertIsNone(self.connection.execute("SELECT to_regclass('whereto.rollback_probe')").fetchone()[0])
        self.assertEqual(migrate(self.connection), 0)

    def test_api_roles_are_denied(self):
        for role in ('anon','authenticated','service_role'):
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with self.connection.transaction():
                    self.connection.execute('SET LOCAL ROLE ' + role)
                    self.connection.execute('SELECT * FROM whereto.plans')

    def test_primary_keys_nulls_and_timestamps(self):
        self.invalid("INSERT INTO whereto.plans(id,data_mode) VALUES (%s,'mock')", (self.plan,))
        self.invalid('INSERT INTO whereto.plans(data_mode) VALUES (NULL)')
        self.invalid("INSERT INTO whereto.plans(data_mode,updated_at) VALUES ('mock','2000-01-01')")
        self.invalid("INSERT INTO whereto.generated_itineraries(plan_id,option_position,candidate_id,feasibility) VALUES (%s,5,'bad','preview')", (self.plan,))
        created, updated = self.connection.execute('SELECT created_at,updated_at FROM whereto.plans WHERE id=%s', (self.plan,)).fetchone()
        self.assertIsNotNone(created.tzinfo)
        self.assertEqual(created,updated)
