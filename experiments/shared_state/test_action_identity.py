"""New-build replay evidence; no historical evaluator gate is overridden."""
from copy import deepcopy
from datetime import datetime
import json
import sqlite3
import unittest
from unittest.mock import patch
from scripts import task52_q1 as q1
from experiments.shared_state import action_identity as build
from experiments.shared_state.contracts import Denied


class ActionBuildTests(unittest.TestCase):
    def test_exact_current_identity_and_wrong_build_refusal(self):
        self.assertEqual(build.verify_build()['identity'],'52-server-action-bridge-local-v4')
        with patch.object(build,'MANIFEST_SHA','0'*64),self.assertRaises(Denied):build.verify_build()
        from scripts.task52_phase_b2_identity import verify
        with self.assertRaises(ValueError):verify()  # Full B2 source root is intentionally frozen.

    def test_seven_recorded_outputs_current_build_and_frozen_result_equality(self):
        build.verify_build()
        from backend.ai import parse_interpretation
        from backend.interpretation import InterpretationInput,interpret_request
        from scripts import cloud_model52 as original
        from scripts import task52_ordering_v51 as policy
        corpus={c['id']:c for c in json.loads((q1.ROOT/'docs/task52-evaluation-corpus.json').read_text())['cases']}
        frozen=json.loads((q1.ROOT/'docs/task52-q1-openai-replay-v1.json').read_text())['results']
        v51=json.loads((q1.ROOT/'docs/task52-ordering-v51-replay-v1.json').read_text())['openai']
        manifest=json.loads(q1.MANIFEST.read_text());before=q1.private_hashes()
        # Read-only evidence, separately labelled current-build comparison.
        with sqlite3.connect(f'file:{original.STATE}/journal.sqlite?mode=ro&immutable=1',uri=True) as db:
            db.execute('PRAGMA query_only=ON');rows=db.execute("SELECT * FROM attempts WHERE provider='openai' ORDER BY rowid").fetchall()
        self.assertEqual(len(rows),7)
        with patch('requests.sessions.Session.send',side_effect=AssertionError('No provider')),patch('socket.socket.connect',side_effect=AssertionError('No network')):
            for row in rows:
                record=json.loads(row[5]);content,_,status=original.Adapter('openai',None).decode(record['response'])
                self.assertEqual(status,'complete');ai=parse_interpretation(content);raw=ai.model_dump_json();case=corpus[row[1]]
                prior=next(r for r in frozen if r['slot']==list(row[:3]))
                self.assertEqual(q1.digest(record['response']),prior['original']['responseHash'])
                class Recorded:
                    def interpret(self,text):
                        if text!=case['text']:raise AssertionError('Wrong source')
                        return ai.model_copy(deep=True)
                result=interpret_request(InterpretationInput(text=case['text'],calendarTimezone=original.timezone_for(case)),provider=Recorded(),now=datetime.fromisoformat(manifest['clock']['referenceTime'].replace('Z','+00:00')))
                self.assertEqual(q1.digest(result.model_dump(mode='json')),prior['legacy']['resultHash'])
                self.assertEqual(q1.digest(policy.inspect_order(case['text'],ai)),q1.digest(next(r['V51'] for r in v51 if r['slot']==list(row[:3]))))
                self.assertEqual(ai.model_dump_json(),raw)
        self.assertEqual(before,q1.private_hashes())

    def test_27_recorded_qwen_v51_outcomes_unchanged(self):
        build.verify_build()
        from backend.ai import Interpretation
        from scripts import task52_ordering_v51 as policy
        saved=json.loads((q1.ROOT/'backend/evaluation/results-task50e-model-investigation.json').read_text())
        frozen=json.loads((q1.ROOT/'docs/task52-ordering-v51-replay-v1.json').read_text())['qwen']
        sources=json.loads((q1.ROOT/'docs/task52-ordering-qwen-review-v2.json').read_text())['rows']
        self.assertEqual(len(frozen),27)
        for row in frozen:
            old=row['originalV5Comparison'];cohort=old['cohort'];index=old['row']
            ai=Interpretation.model_validate(deepcopy(saved[cohort]['rows'][index]['raw']))
            source=next(r['source'] for r in sources if r['cohort']==cohort and r['row']==index)
            self.assertEqual(q1.digest(policy.inspect_order(source,ai)),q1.digest(row['V51']))
