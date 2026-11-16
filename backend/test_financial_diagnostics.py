"""Sanitized observer formatting only; no database, credentials or provider I/O."""
from types import SimpleNamespace
import unittest
from experiments.shared_state.financial_diagnostics import category,locations


class DiagnosticTests(unittest.TestCase):
    def error(self,message,context=''):
        return SimpleNamespace(diag=SimpleNamespace(message_primary=message,context=context))

    def test_only_identifier_categories_are_exposed(self):
        self.assertEqual(category(self.error('clock_rollback')),'clock_rollback')
        self.assertEqual(category(self.error('canceling statement due to statement timeout')),'statement_timeout')
        self.assertEqual(category(self.error('canceling statement due to user request')),'user_cancellation')
        for message in ['secret=private','SELECT text','user@example.com','x'*81,None,12]:
            self.assertEqual(category(self.error(message)),'redacted')

    def test_context_exposes_function_and_line_never_statement_or_arguments(self):
        context="PL/pgSQL function synthetic_state.finance_guard() line 28 at RAISE\nSQL statement SELECT private_content\nPL/pgSQL function synthetic_state.app_protocol(text,jsonb,text,text,text) line 7 at PERFORM"
        self.assertEqual(locations(self.error('clock_rollback',context)),[
            {'function':'synthetic_state.finance_guard','line':28},
            {'function':'synthetic_state.app_protocol','line':7}])

    def test_missing_or_unrecognized_context_has_no_output(self):
        self.assertEqual(category(Exception()),'redacted')
        self.assertEqual(locations(Exception()),[])
        self.assertEqual(locations(self.error('redacted','raw request or SQL parameters')),[])
