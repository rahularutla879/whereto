"""Offline fictional review records. No provider prices/counts are certified here."""
from copy import deepcopy
import json,unittest
from unittest.mock import patch
from backend.provider_enrollment_review import load_draft,review_bound,template_digest,digest,ReviewError,DRAFT
from backend.ai.openai_candidate import request_bytes
from backend.provider_responses import real_inference_accounting,ProviderResponseError
from backend.action_dispatch import Request
from backend.places import search_body,DiscoveryRequest,SearchArea,ENDPOINT,FIELD_MASK

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.wire=request_bytes('coffee then museum in Baltimore')
        self.policy=dict(provider='openai',account='fictional_project',version='fictional-rate-v1',checkedAt=100,expiresAt=200,priceEvidenceSHA256='a'*64,
          rates=dict(inputMicroUsdPerMillion=1000000,outputMicroUsdPerMillion=2000000),model='gpt-6-luna',modelRevision='fictional-revision',endpoint='https://api.openai.com/v1/responses',
          templateSHA256=template_digest(json.loads(self.wire)),counterVersion='fictional-complete-counter-v1',maxInput=12000,maxOutput=2000,inputMargin=2048,costProfile='input-output-only-reviewed-no-extras-v1')
        self.count=dict(payloadSHA256=digest(self.wire),provider='openai',account='fictional_project',modelRevision='fictional-revision',model='gpt-6-luna',counterVersion=self.policy['counterVersion'],inputTokens=100,checkedAt=100,expiresAt=200)
    def bound(self,p=None,w=None,c=None,now=150):return review_bound(p or self.policy,w or self.wire,count=self.count if c is None else c,now=now)
    def test_review_arithmetic_cannot_authorize_dispatch(self):
        x=self.bound();self.assertEqual(x.maximum_micro_usd,6148);self.assertEqual(x.units,2148)
        with self.assertRaises(ProviderResponseError):real_inference_accounting(x)
    def test_disabled_source_pinned_draft_is_not_enrollment(self):
        d=load_draft();self.assertFalse(d['enabled']);self.assertFalse(d['dispatchAuthorized']);self.assertIsNone(d['grant'])
        with self.assertRaises(ReviewError):review_bound(d['applicationModel'],self.wire,count=self.count,now=150)
        with patch.object(type(DRAFT),'read_bytes',return_value=b'{}'):
            with self.assertRaises(ReviewError):load_draft()
    def test_dependency_source_substitution_is_rejected(self):
        original=type(DRAFT).read_bytes
        def read(path):
            if str(path).endswith('backend/provider_responses.py'):return b'changed'
            return original(path)
        with patch.object(type(DRAFT),'read_bytes',read):
            with self.assertRaises(ReviewError):load_draft()
    def test_price_freshness_missing_and_malformed(self):
        for change in [dict(rates=None),dict(priceEvidenceSHA256=None),dict(checkedAt=151),dict(expiresAt=150),dict(checkedAt=0,expiresAt=86401),dict(rates={'inputMicroUsdPerMillion':1.2,'outputMicroUsdPerMillion':1}),dict(rates={'inputMicroUsdPerMillion':True,'outputMicroUsdPerMillion':1})]:
            with self.subTest(change=change),self.assertRaises(ReviewError):self.bound({**self.policy,**change})
    def test_calendar_day_rollover_expires_review_never_renews_a_grant(self):
        p={**self.policy,'checkedAt':86399,'expiresAt':86500}
        c={**self.count,'checkedAt':86399,'expiresAt':86500}
        with self.assertRaises(ReviewError):self.bound(p,c=c,now=86400)
    def test_count_missing_stale_incomplete_or_different_payload(self):
        for count in [{},{**self.count,'inputTokens':0},{**self.count,'inputTokens':True},{**self.count,'inputTokens':12000},{**self.count,'expiresAt':150},{**self.count,'payloadSHA256':'b'*64},{**self.count,'counterVersion':'forged'},{**self.count,'provider':'google'},{**self.count,'account':'other'},{**self.count,'modelRevision':'other'},{**self.count,'actualUsage':12}]:
            with self.subTest(count=count),self.assertRaises(ReviewError):self.bound(c=count)
    def test_model_endpoint_template_and_extra_cost_substitution(self):
        for change in [dict(model='other'),dict(endpoint='https://example.com'),dict(templateSHA256='b'*64),dict(costProfile='unknown')]:
            with self.subTest(change=change),self.assertRaises(ReviewError):self.bound({**self.policy,**change})
        for change in [dict(reasoning={'effort':'high'}),dict(max_output_tokens=2001),dict(tools=[{}]),dict(store=True),dict(service_tier='priority')]:
            b=json.loads(self.wire);b.update(change);w=json.dumps(b,sort_keys=True,separators=(',',':')).encode()
            with self.subTest(change=change),self.assertRaises(ReviewError):self.bound(w=w,c={**self.count,'payloadSHA256':digest(w)})
    def test_rounding_and_overflow(self):
        p={**self.policy,'rates':{'inputMicroUsdPerMillion':1,'outputMicroUsdPerMillion':1}}
        self.assertEqual(self.bound(p).maximum_micro_usd,2)
        with self.assertRaises(ReviewError):self.bound({**self.policy,'rates':{'inputMicroUsdPerMillion':10**13,'outputMicroUsdPerMillion':1}})
    def test_canonical_bytes_and_invalid_source_shape(self):
        with self.assertRaises(ReviewError):self.bound(w=self.wire+b' ',c={**self.count,'payloadSHA256':digest(self.wire+b' ')})
        with self.assertRaises(ReviewError):template_digest({'input':[None]})
    def test_maps_reuses_canonical_sku_and_units(self):
        p={k:self.policy[k] for k in ('account','version','checkedAt','expiresAt','priceEvidenceSHA256')}
        p.update(provider='google',rates={'search_pro':32000,'matrix_element':5000,'matrix_pro_element':10000})
        w=Request.make('search','POST',ENDPOINT,FIELD_MASK,search_body(DiscoveryRequest(activity='coffee',destination=SearchArea(name='Baltimore')),3)).canonical
        x=review_bound(p,w,now=150);self.assertEqual((x.model_or_sku,x.units,x.maximum_micro_usd),('search_pro',1,32000))
        altered=json.loads(w);altered['mask']='*'
        with self.assertRaises(ProviderResponseError):review_bound(p,json.dumps(altered,sort_keys=True,separators=(',',':')).encode(),now=150)
        with self.assertRaises(ReviewError):review_bound({**p,'rates':{**p['rates'],'details':20000}},w,now=150)
    def test_maps_matrix_dimensions_and_mode_price(self):
        from backend.routes import matrix_body,RoutePoint,ENDPOINT,FIELD_MASK
        p={k:self.policy[k] for k in ('account','version','checkedAt','expiresAt','priceEvidenceSHA256')};p.update(provider='google',rates={'search_pro':32000,'matrix_element':5000,'matrix_pro_element':10000})
        point=RoutePoint(id='a',place_id='Fixture_a')
        for mode,price in [('drive',10000),('walk',5000)]:
            w=Request.make('matrix','POST',ENDPOINT,FIELD_MASK,matrix_body([point],[point],mode)).canonical
            self.assertEqual(review_bound(p,w,now=150).maximum_micro_usd,price)

if __name__=='__main__':unittest.main()
