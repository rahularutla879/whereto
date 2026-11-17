"""Offline responses only; no real network, key, account or paid-journal access."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from backend.provider_responses import HTTPResult
from scripts import task52b_readiness as r


def response(value, **kw):
    return HTTPResult(200, json.dumps(value).encode(), **kw)


def good():
    return (response({'id': r.MODEL, 'object': 'model', 'created': 1, 'owned_by': 'FICTIONAL', 'extra': 'metadata'}),
            response({'object': 'response.input_tokens', 'input_tokens': 100}))


class ReadinessTests(unittest.TestCase):
    def test_exact_two_requests_and_no_generation(self):
        a,b=r.requests()
        self.assertEqual((a.method,a.url,a.body),('GET','https://api.openai.com/v1/models/gpt-6-luna',b''))
        self.assertEqual((b.method,b.url),('POST','https://api.openai.com/v1/responses/input_tokens'))
        self.assertEqual(sha256(b.body).hexdigest(),r.COUNT_SHA)
        self.assertEqual(set(json.loads(b.body)),{'model','input','text','reasoning'})
    def test_source_pinned_preparation_stays_disabled(self):
        root=Path(__file__).resolve().parents[1]
        profile=json.loads((root/'docs/task52b-readiness-profile-PROPOSED-v1.json').read_bytes())
        for key in ('enabled','operationalEnrollmentAvailable','ownerApproved','inferenceAuthorized','financialAuthorization'):
            self.assertIs(profile[key],False)
        self.assertEqual(profile['restrictedPermissions'],{'listModels':'Read','responses':'Read','unrelated':'None','automaticExpansion':False})
        self.assertFalse(profile['supportInformation']['independentlyVerified'])
        self.assertFalse(profile['supportInformation']['operationalOrFinancialApproval'])
        build=json.loads((root/'docs/task52b-readiness-build-v1.json').read_bytes())
        self.assertFalse(build['activated'])
        for name,expected in build['filesSHA256'].items():
            self.assertEqual(sha256((root/name).read_bytes()).hexdigest(),expected,name)
    def test_success_captures_exact_raw_without_authorizing(self):
        f=r.FictionalReadiness(good());self.addCleanup(f.close)
        result=f.run();self.assertTrue(result['fixtureValidated']);self.assertFalse(result['financialAuthorization'])
        self.assertEqual(f.sent,list(r.requests()));self.assertEqual(result['results'][1]['inputTokens'],100)
        self.assertEqual(result['results'][1]['generationSHA256'],r.REQUEST_SHA)
        self.assertEqual(len(list(f.directory.glob('intent-*'))),2)
        self.assertEqual(json.loads((f.directory/'raw-2.json').read_bytes())['sha256'],good()[1].digest)
    def test_model_mismatch_blocks_count(self):
        for value in ({'id':'other','object':'model','created':1,'owned_by':'x'}, {'id':r.MODEL,'object':'model','created':True,'owned_by':'x'}):
            f=r.FictionalReadiness((response(value),good()[1]));self.addCleanup(f.close)
            with self.assertRaisesRegex(r.Refused,'model_identity'):f.run()
            self.assertEqual(len(f.sent),1)
    def test_permission_denial_is_terminal_never_broadens(self):
        for stage in (0,1):
            for status in (401,403):
                replies=list(good());replies[stage]=HTTPResult(status,b'{"error":"FICTIONAL"}')
                f=r.FictionalReadiness(tuple(replies));self.addCleanup(f.close)
                with self.assertRaisesRegex(r.Refused,'permission_denied'):f.run()
                self.assertEqual(len(f.sent),stage+1)
                with self.assertRaisesRegex(r.Refused,'replay'):f.run()
                self.assertEqual(len(f.sent),stage+1)
    def test_redirect_error_truncation_and_bad_json_refuse(self):
        for bad in (HTTPResult(307,b'{}'),HTTPResult(429,b'{}'),HTTPResult(500,b'{}'),HTTPResult(200,b'{}',complete=False),HTTPResult(200,b'not-json'),HTTPResult(200,b'{}',content_type='text/html'),HTTPResult(200,b'{"object":"response.input_tokens","input_tokens":1,"input_tokens":2}')):
            f=r.FictionalReadiness((good()[0],bad));self.addCleanup(f.close)
            with self.assertRaises(r.Refused):f.run()
            with self.assertRaisesRegex(r.Refused,'replay'):f.run()
            self.assertEqual(len(f.sent),2)
    def test_invalid_count_and_excessive_input_refuse(self):
        for n in (None,True,0,-1,1.0,'4',9953,2**63):
            with self.subTest(n=n),self.assertRaises(r.Refused):
                r.validate_response(r.requests()[1],response({'object':'response.input_tokens','input_tokens':n}))
        self.assertEqual(r.validate_response(r.requests()[1],response({'object':'response.input_tokens','input_tokens':9952}))['inputBound'],12000)
    def test_unknown_count_fields_and_wrong_object_refuse(self):
        for v in ({'object':'other','input_tokens':1},{'object':'response.input_tokens','input_tokens':1,'model':'other'},[],{'input_tokens':1}):
            with self.assertRaises(r.Refused):r.validate_response(r.requests()[1],response(v))
    def test_method_endpoint_body_and_provider_substitution_refuse(self):
        for q in (r.Request('POST',r.ORIGIN+'/v1/responses',r.requests()[1].body),r.Request('GET','http://api.openai.com/v1/models/'+r.MODEL,b''),r.Request('POST',r.requests()[1].url,r.requests()[1].body+b' ')):
            with self.assertRaisesRegex(r.Refused,'substitution'):r.validate_response(q,good()[1])
    def test_uncertainty_and_runner_replacement_cannot_repeat(self):
        f=r.FictionalReadiness((good()[0],None));self.addCleanup(f.close)
        with self.assertRaisesRegex(r.Refused,'uncertain'):f.run()
        replacement=object.__new__(r.FictionalReadiness)
        replacement.directory=f.directory;replacement.responses=good();replacement.sent=[]
        with self.assertRaisesRegex(r.Refused,'replay'):replacement.run()
        self.assertEqual(replacement.sent,[])
    def test_concurrent_attempts_one_scope_only(self):
        f=r.FictionalReadiness(good());self.addCleanup(f.close)
        def run(_):
            try:f.run();return 'ok'
            except r.Refused:return 'refused'
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(run,range(2)))
        self.assertEqual(sorted(results),['ok','refused']);self.assertEqual(len(f.sent),2)
    def test_real_constructor_never_reads_key_or_opens_network(self):
        key=Mock()
        with patch('socket.socket',side_effect=AssertionError('network')),patch.object(Path,'read_bytes',side_effect=AssertionError('file read')):
            for packet in (None,{'approved':True,'supportSaysFree':True}):
                with self.assertRaisesRegex(r.Refused,'enrollment'):r.ReadinessTransport(packet,credential=key)
        self.assertEqual(key.mock_calls,[])
    def test_only_closed_fictional_responses(self):
        for v in (Mock(),[good()[0],good()[1]],(Mock(),good()[1])):
            with self.assertRaisesRegex(r.Refused,'fictional'):r.FictionalReadiness(v)


class CostTests(unittest.TestCase):
    def setUp(self):
        self.count={'project':'FICTIONAL-PROJECT','model':r.MODEL,'modelRevision':'FICTIONAL-REVISION','generationSHA256':r.REQUEST_SHA,'countSHA256':r.COUNT_SHA,'inputTokens':100,'checkedAt':100,'expiresAt':200}
        self.prices={'project':'FICTIONAL-PROJECT','model':r.MODEL,'modelRevision':'FICTIONAL-REVISION','sourceSHA256':'a'*64,'checkedAt':100,'expiresAt':200,
                     'ratesNanoPerMillion':{'input':100000000,'cached_input':10000000,'cache_write_30m':125000000,'cache_write_12h':250000000,'output':500000000}}
        self.kw={'project':'FICTIONAL-PROJECT','model_revision':'FICTIONAL-REVISION','prices':self.prices,'now':150,'extras':{'tools':0,'separate_reasoning':0,'other_fees':0},'uplift_bps':0}
    def quote(self,**kw):return r.conservative_quote(self.count,**(self.kw|kw))
    def test_conservative_cache_writes_no_guaranteed_discount(self):
        q=self.quote();self.assertEqual(q['maximumNanodollars'],1268500)
        self.assertEqual(q['inputRateNanoPerMillion'],125000000);self.assertEqual(q['cacheTTL'],'30m');self.assertFalse(q['cacheWrite12hApplicable']);self.assertFalse(q['approved']);self.assertFalse(q['financialAuthorization'])
    def test_high_input_exceeds_unchanged_proposal_not_new_grant(self):
        self.count['inputTokens']=9952;q=self.quote()
        self.assertEqual(q['maximumNanodollars'],2500000);self.assertTrue(q['withinProposedCeiling']);self.assertFalse(q['approved'])
        q=self.quote(uplift_bps=1000)
        self.assertEqual(q['maximumNanodollars'],2750000);self.assertFalse(q['withinProposedCeiling']);self.assertEqual(q['proposedCeilingNanodollars'],2500000)
    def test_unknown_pricing_and_fees_refuse(self):
        for k in r.RATE_KEYS:
            p=deepcopy(self.prices);p['ratesNanoPerMillion'].pop(k)
            with self.assertRaises(r.Refused):self.quote(prices=p)
        for kw in ({'prices':None},{'extras':None},{'extras':{'tools':0,'separate_reasoning':None,'other_fees':0}},{'uplift_bps':None}):
            with self.assertRaises(r.Refused):self.quote(**kw)
    def test_modified_model_payload_revision_and_stale_evidence_refuse(self):
        for k,v in [('project','other'),('model','other'),('modelRevision','other'),('generationSHA256','b'*64),('countSHA256','b'*64),('inputTokens',9953),('checkedAt',151),('expiresAt',150)]:
            old=self.count[k];self.count[k]=v
            with self.assertRaises(r.Refused):self.quote()
            self.count[k]=old
        p=deepcopy(self.prices);p['expiresAt']=150
        with self.assertRaises(r.Refused):self.quote(prices=p)
    def test_output_limits_preserve_frozen_request(self):
        for n in (0,-1,True,None,1999,2001,2**63):
            with self.assertRaises(r.Refused):self.quote(output_limit=n)
    def test_upward_rounding_all_extras_and_uplift(self):
        for k in self.prices['ratesNanoPerMillion']:self.prices['ratesNanoPerMillion'][k]=1
        q=self.quote(extras={'tools':1,'separate_reasoning':2,'other_fees':3},uplift_bps=1)
        self.assertEqual(q['maximumNanodollars'],9);self.assertEqual(q['upliftNanodollars'],1)
    def test_money_overflow_refuses(self):
        with self.assertRaises(r.Refused):self.quote(extras={'tools':10**12,'separate_reasoning':10**12,'other_fees':0})

    def test_prices_wrong_account_or_revision_refuse(self):
        for key in ('project','modelRevision'):
            p=deepcopy(self.prices);p[key]='OTHER'
            with self.assertRaises(r.Refused):self.quote(prices=p)
        for key in ('project','modelRevision'):
            old=self.count[key];self.count[key]='bad identity\n'
            with self.assertRaises(r.Refused):self.quote(**({'project':'bad identity\n'} if key=='project' else {'model_revision':'bad identity\n'}))
            self.count[key]=old
