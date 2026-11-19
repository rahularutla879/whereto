"""Offline source/retention guards; no account, credential or network access."""
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import ast,json,unittest
from .projection import backend
from .sql import application_sql
from .identity import verify_application

class Tests(unittest.TestCase):
    def test_exact_reproducible_backend_source_cohort(self):
        doc=json.loads((Path(__file__).parent/'sources.json').read_bytes())
        with TemporaryDirectory() as temp:
            target=Path(temp)/'backend';manifest=backend(target)
            actual={'backend/'+str(p.relative_to(target)):sha256(p.read_bytes()).hexdigest() for p in target.rglob('*.py')}
            self.assertEqual(actual,doc['backendOutputs']);self.assertFalse(manifest['releaseEligible'])
    def test_normal_unprojected_application_is_not_an_enrolled_real_cohort(self):
        with self.assertRaises(ValueError):verify_application()
    def test_no_fixture_files_or_unmetered_provider_fallback(self):
        with TemporaryDirectory() as temp:
            target=Path(temp)/'backend';backend(target)
            for p in target.rglob('*.py'):
                self.assertFalse(p.name.startswith(('test_','run_')))
                self.assertNotIn(p.name,('testing_clock.py','journey_fixtures.py','real_fixtures.py'))
            for name in ('places_transport.py','routes_transport.py'):
                text=(target/name).read_text();self.assertIn('real_application.native import require_native',text);self.assertIn('direct_provider_unavailable',text);self.assertNotIn('requests.',text)
            self.assertIn('raise AIError',(target/'ai/ollama.py').read_text())
    def test_retention_dependencies_never_populate_global_sessions(self):
        with TemporaryDirectory() as temp:
            target=Path(temp)/'backend';backend(target)
            for name,cls,methods in [('option_sessions.py','OptionSessions',('create',)),('venue_details.py','DetailsSessions',('create','extend'))]:
                node=next(n for n in ast.parse((target/name).read_text()).body if isinstance(n,ast.ClassDef) and n.name==cls)
                for method in methods:
                    fn=next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name==method)
                    self.assertEqual(len(fn.body),1);self.assertIsInstance(fn.body[0],ast.Return);self.assertIsNone(fn.body[0].value.value)
    def test_sql_is_additive_immutable_and_preserves_financial_delegate(self):
        text=application_sql();self.assertIn('real_approve_google_batch',text);self.assertIn('provider_state.real_google_plan(wire)',text)
        self.assertIn('provider_state.app_protocol(a,p,env,ep,proof)',text);self.assertIn('real_response_receipt_required',text)
        self.assertIn('REVOKE EXECUTE ON FUNCTION provider_state.app_protocol',text)
        self.assertNotIn('INSERT INTO provider_rules.configuration',text);self.assertNotRegex(text,r'(?im)^\s*(?:DROP|UPDATE)\s+[A-Za-z_]')

if __name__=='__main__':unittest.main()
