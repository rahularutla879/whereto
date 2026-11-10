"""Q3 fictional in-memory protocol model. NOT a paid journal or live runner.

Only opaque baseline hashes/slot identities are copied, never original rows,
responses, root configuration or credentials. SQLite is always :memory:.
No file-based approval, financial authority, socket or transport is returned.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
import sqlite3
import threading
import unittest
from scripts import task52_q1 as q1
from scripts import task52_q3 as q3
from scripts import cloud_model52_ordering_v4 as policy
from backend.ai import Interpretation


class Refused(ValueError):pass


class FictionalProtocol:
    """State-transition tests only, not trusted reviewer/dispatch implementation."""
    def __init__(self,plan):
        self.plan=deepcopy(plan);self.plan_hash=q1.digest(plan);self.root=plan['baseline']['rootHash']
        self.anchors=deepcopy(plan['baseline']['rows']);self.consumed={tuple(a['slot']) for a in self.anchors}
        self.base_total=10;self.base_provider=7;self.base_spend=47366625
        self.extra_cap=12500000;self.limit=5;self.lock=threading.Lock();self.owner=None
        self.db=sqlite3.connect(':memory:',check_same_thread=False)
        self.db.executescript('CREATE TABLE anchors(n INTEGER PRIMARY KEY, slot TEXT, digest TEXT); CREATE TABLE events(n INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, operation INTEGER, data TEXT); CREATE TABLE grants(id TEXT PRIMARY KEY);')
        self.db.executemany('INSERT INTO anchors VALUES (?,?,?)',[(a['ordinal'],json.dumps(a['slot']),a['rowHash']) for a in self.anchors]);self.db.commit()
        self.reviewed=False;self.granted=False;self.fresh=False

    def close(self):self.db.close()

    def check_anchors(self):
        actual=self.db.execute('SELECT n,slot,digest FROM anchors ORDER BY n').fetchall()
        expected=[(a['ordinal'],json.dumps(a['slot']),a['rowHash']) for a in self.anchors]
        if actual!=expected or self.root!=self.plan['baseline']['rootHash']:raise Refused('Original anchors changed')
        if self.anchors[-1]['originalState']!='recorded_halted':raise Refused('Historical halt must remain')

    def approve_fictional(self,grant='FICTIONAL-NEW-Q3-SCOPE',*,reviewed=True,fresh=True):
        self.check_anchors()
        if grant!='FICTIONAL-NEW-Q3-SCOPE':raise Refused('Old/unknown approval cannot resume')
        try:
            with self.db:self.db.execute('INSERT INTO grants VALUES (?)',(grant,))
        except sqlite3.IntegrityError:raise Refused('Duplicate approval') from None
        self.granted=True;self.reviewed=reviewed;self.fresh=fresh

    def events(self,kind=None):
        return [(n,k,o,json.loads(d)) for n,k,o,d in self.db.execute('SELECT * FROM events ORDER BY n') if kind is None or k==kind]

    def append(self,kind,op,data):
        with self.db:
            cur=self.db.execute('INSERT INTO events(kind,operation,data) VALUES (?,?,?)',(kind,op,json.dumps(data,sort_keys=True)))
            return cur.lastrowid

    @contextmanager
    def runner(self):
        if not self.lock.acquire(False):raise Refused('Concurrent runner')
        self.owner=threading.get_ident()
        try:yield
        finally:self.owner=None;self.lock.release()

    def reserve_simulated(self,slot,*,candidate=None,input_bound=12000,output_bound=2000,reservation=2500000):
        self.check_anchors()
        if self.owner!=threading.get_ident():raise Refused('Runner ownership required')
        if not self.granted or not self.reviewed or not self.fresh:raise Refused('Missing independent review/approval/readiness')
        if self.events('HALT'):raise Refused('Child halt is persistent')
        if candidate is not None and q1.digest(candidate)!=self.plan_hash:raise Refused('Source/config/schema/profile mismatch')
        if type(input_bound)is not int or type(output_bound)is not int or not 0<input_bound<=12000 or not 0<output_bound<=2000:
            raise Refused('Token caps')
        if type(reservation)is not int or reservation!=2500000:raise Refused('Full reservation required')
        reserved=self.events('RESERVE');n=len(reserved)
        if tuple(slot) in self.consumed or any(tuple(r[3]['slot'])==tuple(slot) for r in reserved):raise Refused('Consumed slot, never retry')
        if n>=self.limit or n>=len(self.plan['slots']):raise Refused('Incremental attempt ceiling')
        if list(slot)!=self.plan['slots'][n]['slot']:raise Refused('Unexpected next slot')
        if n and not any(r[2]==reserved[-1][0] for r in self.events('REVIEW')):raise Refused('Uncertain/unreviewed previous operation')
        if self.base_total+n>=594 or self.base_provider+n>=198:raise Refused('Original attempt ceiling')
        if (n+1)*reservation>self.extra_cap or self.exposure_simulated()+reservation>12000000000:raise Refused('Spend ceiling')
        return self.append('RESERVE',0,{'slot':list(slot),'charge':reservation,'kind':'FICTIONAL_ONLY'})

    def intent_simulated(self,op):
        if not any(r[0]==op for r in self.events('RESERVE')) or any(r[2]==op for r in self.events('INTENT')):
            raise Refused('Missing/duplicate dispatch intent')
        self.append('INTENT',op,{'networkRequestSent':False})

    def result_simulated(self,op,*,raw='correct',legacy='accepted',guard='compatible',critical=(),fields_complete=True,observed_liability=2500000):
        if not any(r[2]==op for r in self.events('INTENT')) or any(r[2]==op for r in self.events('RESULT')):raise Refused('Result ownership/replay')
        if type(observed_liability)is not int or observed_liability<0:raise Refused('Invalid observed liability')
        data={'raw':raw,'legacy':legacy,'guard':guard,'critical':list(critical),'complete':fields_complete,'observed_liability':observed_liability}
        digest=q1.digest(data);self.append('RESULT',op,{'outcome':data,'hash':digest})
        slot=next(r[3]['slot'] for r in self.events('RESERVE') if r[0]==op)
        expected_clarification=slot[1]=='journey-21'
        okay=(raw=='correct' and not critical and fields_complete and observed_liability<=2500000 and
              ((expected_clarification and legacy=='clarify' and guard=='blocked') or
               (not expected_clarification and legacy=='accepted' and guard=='compatible')))
        if not okay:self.append('HALT',op,{'reason':'critical_or_unresolved_or_unexpected_disposition'})
        return digest

    def exposure_simulated(self):
        results={r[2]:r[3]['outcome']['observed_liability'] for r in self.events('RESULT')}
        return self.base_spend+sum(max(r[3]['charge'],results.get(r[0],0)) for r in self.events('RESERVE'))

    def review_simulated(self,op,outcome_hash,*,independent=True):
        row=next((r for r in self.events('RESULT') if r[2]==op),None)
        if (self.events('HALT') or row is None or row[3]['hash']!=outcome_hash
            or q1.digest(row[3]['outcome'])!=row[3]['hash'] or not independent
            or any(r[2]==op for r in self.events('REVIEW'))):
            raise Refused('Unreviewed/stale/replayed/halted response')
        self.append('REVIEW',op,{'fictionalIndependentReview':True,'hash':outcome_hash})

    def crash_simulated(self):self.append('HALT',0,{'reason':'crash; no automatic recovery'})


class ContinuationProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=q3.proposal()

    def fixture(self,*,approved=True,reviewed=True,fresh=True):
        f=FictionalProtocol(self.plan);self.addCleanup(f.close)
        if approved:f.approve_fictional(reviewed=reviewed,fresh=fresh)
        return f

    def test_readonly_proposal_exactly_reproduces_frozen_plan(self):
        self.assertEqual(self.plan,json.loads((q3.e.ROOT/'docs/task52-q3-openai-proposal-v1.json').read_text()))
        self.assertFalse(self.plan['dispatchAuthorized']);self.assertFalse(self.plan['approvalSidecarCreated'])
        self.assertEqual(len(self.plan['baseline']['rows']),10)
        self.assertEqual(self.plan['maxProposedAdditionalReservationNanodollars'],12500000)
        self.assertTrue(all(not s['unresolvedQ1Fields'] and not s['independentRubricApproved'] for s in self.plan['slots']))
        self.assertEqual(self.plan['excludedHomeCase']['V4Issues'],['absence_not_independently_proven'])

    def test_proposed_configuration_and_review_documents_bind_exact_hashes(self):
        p=self.plan;worksheet=json.loads((q3.e.ROOT/'docs/task52-q3-independent-review-v1.json').read_text())
        self.assertEqual(p['successorConfigurationHash'],q1.digest(p['successorVersionSpecification']))
        self.assertEqual(worksheet['proposalDigest'],q1.digest(p))
        self.assertEqual(worksheet['successorConfigurationHash'],p['successorConfigurationHash'])
        self.assertIsNone(p['successorVersionSpecification']['futureEvaluatorImplementationHash'])
        self.assertTrue(all(not row['independentReviewComplete'] for row in worksheet['futureResponses']))
        for name in ('HANDOVER.md','docs/task52-q3-continuation-design.md'):
            self.assertIn(p['successorConfigurationHash'],(q3.e.ROOT/name).read_text())

    def test_all_ten_consumed_slots_refused_and_anchors_preserved(self):
        f=self.fixture();anchors=f.db.execute('SELECT * FROM anchors').fetchall()
        with f.runner():
            for a in self.plan['baseline']['rows']:
                with self.assertRaises(Refused):f.reserve_simulated(a['slot'])
        self.assertEqual(f.db.execute('SELECT * FROM anchors').fetchall(),anchors)
        self.assertFalse(f.events('RESERVE'))

    def test_old_approval_duplicate_grant_wrong_order_and_unreviewed_refused(self):
        f=self.fixture(approved=False)
        with self.assertRaises(Refused):f.approve_fictional('old-five-slot-approval')
        f.approve_fictional()
        with self.assertRaises(Refused):f.approve_fictional()
        with f.runner():
            with self.assertRaises(Refused):f.reserve_simulated(self.plan['slots'][1]['slot'])
        for kw in ({'approved':False},{'reviewed':False},{'fresh':False}):
            other=self.fixture(**kw)
            with other.runner(),self.assertRaises(Refused):other.reserve_simulated(self.plan['slots'][0]['slot'])

    def test_wrong_version_schema_source_graph_and_root_refused(self):
        f=self.fixture()
        for mutate in (lambda p:p['successorVersionSpecification'].update(runtime='wrong'),
                       lambda p:p['successorVersionSpecification'].update(wireSchemaHash='wrong'),
                       lambda p:p['slots'][0].update(sourceSHA256='wrong'),
                       lambda p:p['slots'][0]['Q1FieldExpectations']['mandatory_order']['expected'].update(requiredReachability=[[0,1]])):
            bad=deepcopy(self.plan);mutate(bad)
            with f.runner(),self.assertRaises(Refused):f.reserve_simulated(self.plan['slots'][0]['slot'],candidate=bad)
        f.root='changed'
        with f.runner(),self.assertRaises(Refused):f.reserve_simulated(self.plan['slots'][0]['slot'])
        f=self.fixture();f.db.execute("UPDATE anchors SET digest='wrong' WHERE n=10")
        with f.runner(),self.assertRaises(Refused):f.reserve_simulated(self.plan['slots'][0]['slot'])

    def test_global_provider_incremental_budget_and_token_ceiling_refused(self):
        for attr,value in (('base_total',594),('base_provider',198),('base_spend',12000000000),('extra_cap',2499999),('limit',0)):
            f=self.fixture();setattr(f,attr,value)
            with f.runner(),self.assertRaises(Refused):f.reserve_simulated(self.plan['slots'][0]['slot'])
            self.assertFalse(f.events('RESERVE'))
        for kw in ({'input_bound':12001},{'output_bound':2001},{'input_bound':True},{'reservation':1}):
            f=self.fixture()
            with f.runner(),self.assertRaises(Refused):f.reserve_simulated(self.plan['slots'][0]['slot'],**kw)

    def test_crash_before_reserve_and_before_or_after_intent_never_retry(self):
        for stage in ('before_reserve','reserved_before_send','intent_uncertain'):
            f=self.fixture()
            with f.runner():
                if stage!='before_reserve':
                    op=f.reserve_simulated(self.plan['slots'][0]['slot'])
                    if stage=='intent_uncertain':f.intent_simulated(op)
                f.crash_simulated()
                with self.assertRaises(Refused):f.reserve_simulated(self.plan['slots'][0]['slot'])
            self.assertEqual(len(f.events('RESERVE')),0 if stage=='before_reserve' else 1)
            self.assertTrue(f.events('HALT'))

    def test_concurrent_runner_and_uncertain_unreviewed_response_block(self):
        f=self.fixture();out=[]
        def compete():
            try:
                with f.runner():out.append('acquired')
            except Refused:out.append('excluded')
        with f.runner():
            t=threading.Thread(target=compete);t.start();t.join();self.assertEqual(out,['excluded'])
            op=f.reserve_simulated(self.plan['slots'][0]['slot']);f.intent_simulated(op)
            with self.assertRaises(Refused):f.intent_simulated(op)
            with self.assertRaises(Refused):f.reserve_simulated(self.plan['slots'][1]['slot'])
            h=f.result_simulated(op)
            with self.assertRaises(Refused):f.review_simulated(op,'wrong')
            with self.assertRaises(Refused):f.review_simulated(op,h,independent=False)
            with self.assertRaises(Refused):f.reserve_simulated(self.plan['slots'][1]['slot'])

    def test_raw_critical_or_guard_or_unresolved_failure_halts_even_safe_rejection(self):
        for kw in ({'raw':'incorrect','guard':'blocked','critical':['invented_order']},
                   {'critical':['wrong_optionality']},{'critical':['wrong_endpoint']},
                   {'critical':['missing_repeat']},{'guard':'blocked'},{'fields_complete':False}):
            f=self.fixture()
            with f.runner():
                op=f.reserve_simulated(self.plan['slots'][0]['slot']);f.intent_simulated(op);h=f.result_simulated(op,**kw)
                with self.assertRaises(Refused):f.review_simulated(op,h)
                with self.assertRaises(Refused):f.reserve_simulated(self.plan['slots'][1]['slot'])
            self.assertEqual(f.events('RESERVE')[0][3]['charge'],2500000)

    def test_five_successful_fictional_reviews_keep_original_halt_and_all_reservations(self):
        f=self.fixture()
        with f.runner():
            for slot in self.plan['slots']:
                op=f.reserve_simulated(slot['slot']);f.intent_simulated(op)
                h=f.result_simulated(op,legacy='clarify' if slot['slot'][1]=='journey-21' else 'accepted',
                                     guard='blocked' if slot['slot'][1]=='journey-21' else 'compatible')
                f.review_simulated(op,h)
            with self.assertRaises(Refused):f.reserve_simulated(['openai','journey-02',2])
        self.assertEqual(sum(r[3]['charge'] for r in f.events('RESERVE')),12500000)
        self.assertEqual(len(f.events('RESERVE'))+f.base_total,15)
        self.assertEqual(f.base_spend+12500000,59866625)
        f.check_anchors();self.assertEqual(f.anchors[-1]['originalState'],'recorded_halted')

    def test_lower_usage_never_refunds_and_observed_overage_is_retained_and_halts(self):
        for observed in (1000,3000000):
            f=self.fixture()
            with f.runner():
                op=f.reserve_simulated(self.plan['slots'][0]['slot']);f.intent_simulated(op)
                f.result_simulated(op,observed_liability=observed)
            self.assertEqual(f.exposure_simulated(),47366625+max(observed,2500000))
            self.assertEqual(bool(f.events('HALT')),observed>2500000)

    def test_actual_repeated_and_partial_source_proofs_do_not_accept_model_repairs(self):
        def reply(stops,edge,*,optional=()):
            return Interpretation.model_validate({'activities':stops,'budget_per_person':None,'location':'Jersey City','date':None,'preferences':[],
                'journey':{'stops':[{'source':s,'requirement':'optional' if i in optional else 'required','evidence':'maybe stop for coffee' if i in optional else s} for i,s in enumerate(stops)],
                    'order':[{'before':a,'after':b,'source':text} for a,b,text in edge],'ordering':'constrained' if edge else 'unspecified'}})
        text='Coffee, museum, then coffee in Jersey City tomorrow, return to the starting point within three hours.'
        ai=reply(['Coffee','museum','coffee'],[(1,2,'museum, then coffee')]);good=policy.inspect_order(text,ai)
        self.assertEqual(good['trustedGraph'],[[1,2]])
        data=ai.model_dump(mode='json');data['journey']['order'].append({'before':0,'after':1,'source':'Coffee, museum, then'})
        bad=Interpretation.model_validate(data);r=policy.inspect_order(text,bad)
        self.assertIsNone(r['trustedGraph']);self.assertIn([0,1],r['unsupportedModelEdges'])
        self.assertIn([1,2],[[p['before'],p['after']] for p in r['source']['proofs']])
        missing=ai.model_copy(deep=True);missing.journey.stops.pop();missing.activities.pop()
        self.assertIsNone(policy.inspect_order(text,missing)['trustedGraph'])
        text='Visit a pharmacy before the bank; get coffee whenever convenient, in Jersey City tomorrow.'
        ai=reply(['pharmacy','bank','coffee'],[(0,1,'pharmacy before the bank')]);self.assertEqual(policy.inspect_order(text,ai)['trustedGraph'],[[0,1]])
        ai.journey.stops[2].requirement='optional';self.assertIsNone(policy.inspect_order(text,ai)['trustedGraph'])

    def test_changed_origin_endpoint_is_not_silently_repaired(self):
        from backend.journey import validate_journey,REPHRASE
        corpus=json.loads(q3.e.CORPUS.read_text())['cases']
        case=next(c for c in corpus if c['id']=='journey-10')
        ai=Interpretation.model_validate(case['expectedExtraction']);ai.journey.endpoint.kind='home'
        explanation,needs_answer=validate_journey(case['text'],ai)
        self.assertEqual(explanation,REPHRASE)
        self.assertTrue(needs_answer)
        self.assertEqual(ai.journey.endpoint.kind,'home')


if __name__=='__main__':unittest.main()
