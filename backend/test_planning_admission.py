"""Fake-only legacy equivalence and server-admission foundation regressions."""
from contextvars import copy_context
from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch
import unittest

from pydantic import ValidationError
from backend.ai import Interpretation
from backend.interpretation import InterpretationInput, interpret_request
from backend.journey_fixtures import CASES
from backend.planning_admission import (AdmissionRegistry, AdmissionReceipt, AdmissionError,
    require_foundation_for_test, guard_provider, guard_ordinary)
from backend.validation_phases import validate_legacy, LEGACY_PROFILE
from backend.provider_budget import ProviderBudget, ProviderLimitError
from backend.real_planning import PlannerInput, real_plans, more_real_plans
from backend.test_real_planning import ENV
from backend.testing_clock import calendar_clock

NOW=datetime(2026,11,8,12,tzinfo=timezone.utc)
TEXT,DATA,_=CASES[0]


class PlanningAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ,ENV,clear=True))
        self.enterContext(calendar_clock(NOW))
        self.enterContext(patch('requests.sessions.Session.send',side_effect=AssertionError('No live requests')))
        self.clock=0.
        self.registry=AdmissionRegistry(clock=lambda:self.clock)
        self.scope=self.registry.new_scope()
        self.input=InterpretationInput(text=TEXT)
        self.budget=ProviderBudget()

    def issue(self, *, scope=None,revision=1,value=None,data=None,execution=None):
        provider=Mock();provider.interpret.return_value=Interpretation.model_validate(data or DATA)
        result=self.registry.validate(value or self.input,scope or self.scope,revision,provider,
                                      now=NOW,execution=execution)
        self.assertEqual(provider.interpret.call_count,0 if value and value.pending else 1)
        return result

    def candidate(self, outcome, **execution):
        return PlannerInput.model_validate({**outcome.disposition.result.request.model_dump(),**execution})

    def attempt(self, payload):
        guard_ordinary(payload)
        with self.budget.outing().reserve('search','synthetic-request'):
            return 'fake-work'

    def test_all_25_interpretations_and_raw_snapshots_match_legacy(self):
        for text,data,_ in CASES:
            with self.subTest(text=text):
                p=Mock();p.interpret.return_value=Interpretation.model_validate(data)
                old=interpret_request(InterpretationInput(text=text),p,now=NOW)
                new=validate_legacy(InterpretationInput(text=text),p,now=NOW)
                self.assertEqual(old.model_dump(),new.result.model_dump())
                self.assertEqual(new.raw_model,Interpretation.model_validate(data))
                self.assertEqual(p.interpret.call_count,2)
                self.assertEqual(new.source_kind,'raw_model')

    def test_ordinary_without_journey_gets_legacy_authority_not_v4(self):
        data=dict(DATA);data.pop('journey')
        out=self.issue(data=data)
        self.assertIsNotNone(out.receipt)
        self.assertEqual(self.registry.run(out.receipt,self.scope,1,self.candidate(out),self.attempt),'fake-work')
        self.assertEqual(self.budget._requests,1)

    def test_forged_client_copied_and_cross_registry_handles_fail_without_work(self):
        out=self.issue();candidate=self.candidate(out);work=Mock()
        for receipt in (None,{}, {'_handle':'alleged'},AdmissionReceipt('invented'),replace(out.receipt)):
            with self.assertRaises(AdmissionError):self.registry.run(receipt,self.scope,1,candidate,work)
        other=AdmissionRegistry()
        with self.assertRaises(AdmissionError):other.run(out.receipt,other.new_scope(),1,candidate,work)
        work.assert_not_called();self.assertEqual(self.budget._requests,0)
        self.assertNotIn(TEXT,repr(out));self.assertNotIn(out.receipt._handle,repr(out.receipt))

    def test_revision_policy_and_cross_session_mismatch_fail(self):
        out=self.issue();candidate=self.candidate(out);work=Mock()
        for scope,revision,policy in ((self.registry.new_scope(),1,LEGACY_PROFILE),
                                      (self.scope,2,LEGACY_PROFILE),(self.scope,True,LEGACY_PROFILE),
                                      (self.scope,1,'v4-enforced-v1')):
            with self.assertRaises(AdmissionError):self.registry.run(out.receipt,scope,revision,candidate,work,policy=policy)
        self.issue(revision=2)
        with self.assertRaises(AdmissionError):self.registry.run(out.receipt,self.scope,1,candidate,work)
        with self.assertRaises(AdmissionError):self.issue(revision=2)
        work.assert_not_called()

    def test_modified_stops_date_destination_origin_and_search_geometry_fail(self):
        origin={'point':{'id':'authorized-start','coordinates':{'latitude':0.,'longitude':0.}},
                'source':'manual','explicitly_authorized':True,'precision':'address_or_place'}
        out=self.issue(execution={'startingLocation':origin,'locationFirst':True})
        candidate=self.candidate(out,startingLocation=origin,locationFirst=True)
        work=Mock()
        for changes in ({'activities':['food','museum']},{'location':'Different city'},
                        {'date':candidate.date.replace(day=10)}, {'useOriginAsSearchAnchor':True},
                        {'startingLocation':None},{'searchRadius':500.}):
            with self.assertRaises(AdmissionError):
                self.registry.run(out.receipt,self.scope,1,candidate.model_copy(update=changes),work)
        work.assert_not_called()
        self.registry.run(out.receipt,self.scope,1,candidate,lambda p:self.assertIsNot(p,candidate))

    def test_replay_exception_expiry_and_invalidation_do_not_restore_authority(self):
        out=self.issue();candidate=self.candidate(out)
        def uncertain(_):raise TimeoutError('synthetic uncertain work')
        with self.assertRaises(TimeoutError):self.registry.run(out.receipt,self.scope,1,candidate,uncertain)
        with self.assertRaises(AdmissionError):self.registry.run(out.receipt,self.scope,1,candidate,self.attempt)
        out=self.issue(revision=2);self.clock=599.999
        self.registry.run(out.receipt,self.scope,2,self.candidate(out),lambda _:None)
        self.clock=600
        with self.assertRaises(AdmissionError):self.issue(revision=3)
        scope=self.registry.new_scope();out=self.issue(scope=scope)
        self.registry.invalidate(scope)
        with self.assertRaises(AdmissionError):self.registry.run(out.receipt,scope,1,self.candidate(out),self.attempt)

    def test_expiration_during_work_or_borrowed_async_context_blocks_reservation(self):
        out=self.issue();captured=[]
        def late(payload):
            captured.append(copy_context());self.clock=600
            with self.assertRaises(ProviderLimitError):self.attempt(payload)
        self.registry.run(out.receipt,self.scope,1,self.candidate(out),late)
        with self.assertRaises(ProviderLimitError):captured[0].run(guard_provider)
        self.assertEqual(self.budget._requests,0)

    def test_payload_mutation_and_calendar_expiry_block_before_provider_budget(self):
        out=self.issue()
        def mutate(payload):
            payload.location='Invented'
            with self.assertRaises(ProviderLimitError):self.attempt(payload)
        self.registry.run(out.receipt,self.scope,1,self.candidate(out),mutate)
        out=self.issue(revision=2)
        with calendar_clock(datetime(2030,1,1,tzinfo=timezone.utc)):
            with self.assertRaises(ProviderLimitError):
                self.registry.run(out.receipt,self.scope,2,self.candidate(out),self.attempt)
        self.assertEqual(self.budget._requests,0)

    def test_two_workers_cannot_consume_one_receipt_twice(self):
        out=self.issue();candidate=self.candidate(out)
        def worker(_):
            try:self.registry.run(out.receipt,self.scope,1,candidate,lambda p:None);return True
            except AdmissionError:return False
        with ThreadPoolExecutor(2) as pool:self.assertEqual(sorted(pool.map(worker,range(2))),[False,True])

    def test_capacity_fails_closed_without_evicting_live_receipts(self):
        first=None
        for _ in range(50):
            scope=self.registry.new_scope();out=self.issue(scope=scope)
            first=first or (scope,out)
        with self.assertRaises(AdmissionError):self.issue()
        scope,out=first
        self.registry.run(out.receipt,scope,1,self.candidate(out),lambda _:None)

    def test_pending_and_failed_interpretations_never_mint_raw_authority(self):
        out=self.issue();saved=out.disposition.result.pending
        self.assertIsNotNone(saved)
        pending=InterpretationInput(text=TEXT,pending=saved)
        replay=self.issue(value=pending,revision=2)
        self.assertIsNone(replay.receipt)
        self.assertEqual(replay.disposition.source_kind,'legacy_effective_pending')
        self.assertIsNone(replay.disposition.raw_model)
        text,data,_=CASES[11]
        failed=self.issue(value=InterpretationInput(text=text),data=data,revision=3)
        self.assertIsNone(failed.receipt)

    def test_advanced_handoff_binds_order_and_does_not_authorize_provider_calls(self):
        from backend.advanced_planning import Sessions
        text,data,_=CASES[3]
        out=self.issue(value=InterpretationInput(text=text),data=data)
        self.assertIsNotNone(out.receipt)
        payload={'text':text,'result':out.disposition.result,'preferences':out.disposition.input.preferences}
        changed={'text':text,'result':out.disposition.result.model_copy(deep=True),'preferences':payload['preferences']}
        changed['result'].interpretation.journey.order=[]
        with self.assertRaises(AdmissionError):self.registry.run(out.receipt,self.scope,1,changed,lambda _:None)
        sessions=Sessions()
        def handoff(p):
            with patch('backend.advanced_planning.enabled',return_value=True):
                token=sessions.create(p['text'],p['result'],self.budget,p['preferences'])
            self.assertEqual(len(sessions.items),1)
            with self.assertRaises(ProviderLimitError):
                with self.budget.outing().reserve('lookup','not-provider-ready'):pass
            return token
        self.registry.run(out.receipt,self.scope,1,payload,handoff)
        self.assertEqual(self.budget._requests,0)

    def test_no_client_profile_or_validation_fields_and_v4_not_selectable(self):
        for model,base in ((InterpretationInput,{'text':TEXT}),
                           (PlannerInput,{'activities':['food'],'date':'2026-11-09'})):
            for field in ('admissionReceipt','validated','orderingProfile'):
                with self.assertRaises(ValidationError):model.model_validate({**base,field:'invented'})
        provider=Mock()
        with self.assertRaises(ValueError):validate_legacy(self.input,provider,profile='v4')
        provider.interpret.assert_not_called()

    def test_required_scope_blocks_low_level_batches_without_resetting_budgets(self):
        outing=self.budget.outing()
        with require_foundation_for_test():
            for op,kw in [('search',{}),('lookup',{}),('details',{}),('matrix',{'origins':2,'destinations':2})]:
                with self.assertRaises(ProviderLimitError):
                    with outing.reserve(op,'unvalidated-'+op,**kw):self.fail('No work')
            with self.assertRaises(ProviderLimitError):
                with outing.reserve_matrices([('unvalidated',2,2)]):self.fail('No work')
        self.assertEqual(outing.usage()['providerAttempts'],0)
        with outing.reserve('search','legacy-still-default'):pass
        self.assertEqual(self.budget._requests,1)

    def test_existing_provider_quota_still_wins_inside_validated_operation(self):
        from backend.provider_budget import ProviderSettings
        budget=ProviderBudget(ProviderSettings(mode='real',requests_per_session=0))
        out=self.issue()
        def operation(_):
            with self.assertRaises(ProviderLimitError):
                with budget.outing().reserve('search','over-quota'):self.fail('No work')
        self.registry.run(out.receipt,self.scope,1,self.candidate(out),operation)
        self.assertEqual(budget._requests,0)

    def test_stale_revision_or_capacity_rejects_before_any_model_call(self):
        self.issue()
        provider=Mock()
        with self.assertRaises(AdmissionError):
            self.registry.validate(self.input,self.scope,1,provider,now=NOW)
        provider.interpret.assert_not_called()
        for _ in range(49):self.issue(scope=self.registry.new_scope())
        with self.assertRaises(AdmissionError):
            self.registry.validate(self.input,self.registry.new_scope(),1,provider,now=NOW)
        provider.interpret.assert_not_called()

    def test_real_plan_and_options_reject_before_new_session_or_provider_work(self):
        from backend.option_sessions import OptionSessions
        import backend.option_sessions as module
        request=PlannerInput(activities=['food'],location='Jersey City',date='2026-11-09')
        local=OptionSessions()
        with patch('backend.option_sessions.Timer'):
            token=local.create({'request':request})
        before=dict(local.entries)
        with patch.object(module,'option_sessions',local),patch('backend.places_transport.text_search') as send:
            with require_foundation_for_test():
                with self.assertRaises(ProviderLimitError):real_plans(request,self.budget)
                with self.assertRaises(ProviderLimitError):more_real_plans(token,expand_discovery=True)
            self.assertEqual(local.entries,before);send.assert_not_called()
        self.assertEqual(self.budget._requests,0)

    def test_lookup_reference_contact_and_saved_refresh_keep_separate_authorities(self):
        from backend.starting_places import StartingPlaceQuery,lookup_starting_places
        from backend.starting_areas import StartingAreaQuery,suggest_starting_areas
        from backend.venue_details import DetailsSessions
        from backend.saved_refresh import RefreshSessions,RefreshRequest
        from backend.saved_plans import PersistenceError
        from uuid import uuid4
        registry=RefreshSessions();details=DetailsSessions()
        with patch.dict(os.environ,{'WHERETO_START_LOOKUP_DEV':'1','WHERETO_CONTACT_DETAILS_DEV':'1'}):
            detail=details.create({'Synthetic_place'},self.budget.outing())
            request=RefreshRequest(accessToken='x'*43,refreshId=uuid4(),candidateId='chosen')
            document={'dataMode':'real','selectedId':'chosen','itineraries':[{
                'candidateId':'chosen','stops':[{'reference':'Synthetic_place'}]}]}
            with patch('backend.saved_refresh.reopen',return_value=document) as read, \
                 patch('backend.places_transport.text_search') as send, \
                 patch('backend.saved_refresh.fetch_saved_details') as fetch:
                with require_foundation_for_test():
                    for call in (lambda:lookup_starting_places(StartingPlaceQuery(query='Synthetic station'),self.budget),
                                 lambda:suggest_starting_areas(StartingAreaQuery(destination='Jersey City',activities=['food']),self.budget),
                                 lambda:details.get(detail,'Synthetic_place'),
                                 lambda:registry.refresh(request,self.budget)):
                        with self.assertRaises(ProviderLimitError):call()
                read.assert_called_once();send.assert_not_called();fetch.assert_not_called()
                self.assertFalse(registry.entries)
                self.assertFalse(details.entries[detail][3])
            with patch('backend.saved_refresh.reopen',side_effect=PersistenceError(404)):
                with require_foundation_for_test(),self.assertRaises(PersistenceError):registry.refresh(request,self.budget)
        self.assertEqual(self.budget._requests,0)

    def test_advanced_continuation_fails_before_mutating_state_in_required_scope(self):
        from backend.advanced_planning import Sessions,AdvancedInput
        text,data,_=CASES[3]
        result=validate_legacy(InterpretationInput(text=text),
            Mock(interpret=Mock(return_value=Interpretation.model_validate(data))),now=NOW).result
        sessions=Sessions()
        with patch('backend.advanced_planning.enabled',return_value=True):
            with require_foundation_for_test(),self.assertRaises(ProviderLimitError):
                sessions.create(text,result,self.budget,self.input.preferences)
            self.assertFalse(sessions.items)
            token=sessions.create(text,result,self.budget,self.input.preferences)
            session=sessions.items[token]
            with require_foundation_for_test(),self.assertRaises(ProviderLimitError):
                sessions.run(AdvancedInput(token=token))
            self.assertIsNone(session.resolver);self.assertIsNone(session.router)
        self.assertEqual(self.budget._requests,0)

    def test_failed_validation_invalidates_old_revision_before_any_new_provider_work(self):
        out=self.issue();provider=Mock();provider.interpret.return_value={**DATA,'unexpected':'invalid'}
        with self.assertRaises(ValidationError):self.registry.validate(self.input,self.scope,2,provider,now=NOW)
        self.assertEqual(provider.interpret.call_count,1)
        with self.assertRaises(AdmissionError):self.registry.run(out.receipt,self.scope,1,self.candidate(out),self.attempt)
        with self.assertRaises(AdmissionError):self.registry.validate(self.input,self.scope,2,provider,now=NOW)
        self.assertEqual(provider.interpret.call_count,1)
        self.assertEqual(self.budget._requests,0)

    def test_full_fake_planning_uses_owned_request_and_original_accounting(self):
        from backend import test_hitec_geography as fixtures
        fixture=fixtures.HitecPlanningTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        text='box cricket, dinner and movie in hitech city on 2026-11-10'
        value=InterpretationInput(text=text)
        data=dict(activities=['box cricket','dinner','movie'],budget_per_person=None,
                  date=None,location='hitech city',preferences=[])
        execution={'startingLocation':fixtures.ORIGIN,'locationFirst':True}
        out=self.issue(value=value,data=data,execution=execution)
        request=self.candidate(out,**execution)
        result=self.registry.run(out.receipt,self.scope,1,request,lambda p:real_plans(p,self.budget))
        self.assertEqual(len(result.provisionalPlans),3)
        self.assertEqual(result.request.activities,['custom:box cricket','food','movie'])
        self.assertEqual(result.request.location,'hitech city')
        self.assertEqual(result.request.date.isoformat(),'2026-11-10')
        self.assertEqual(fixture.search.call_count,3)
        self.assertGreater(self.budget._requests,3)

    def test_raw_snapshot_is_immutable_and_not_a_shared_model_reference(self):
        out=self.issue()
        before=out.disposition.raw_snapshot
        copy=out.disposition.raw_model;copy.activities=['Invented']
        self.assertEqual(out.disposition.raw_snapshot,before)
        self.assertEqual(out.disposition.raw_model.activities,DATA['activities'])
