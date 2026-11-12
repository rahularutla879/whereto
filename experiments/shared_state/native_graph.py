"""Bounded data graph for reviewed native factories; no executable serialization."""
from datetime import date,datetime
from decimal import Decimal
from enum import Enum
import importlib
import math
from time import monotonic
from uuid import UUID
from pydantic import BaseModel,HttpUrl
from experiments.shared_state.contracts import Denied
from experiments.shared_state.evidence_models import plain

VERSION='52-native-session-reconstruction-local-v1'
MODULES=('models','contracts','ai','journey','interpretation','location_policy','routes','places','venue_models','ranking','stop_resolution','advanced_routing','advanced_timing','advanced_planning','advanced_preferences','saved_plans','saved_advanced','starting_areas','starting_places','provider_budget','hours','feasibility','quality','evidence','price','constraints','activity_rules','hours_policy','venue_quality','location_context','real_planning')
FIELDS={
 'Session':set('actions beyond budget_scope candidates closure_offers closure_overrides configuration context current_ids date_answer departure details_token durations expires explicit_overrides initial_fill_done initial_fill_elements journey last latencies limitation near_origin offerable origin outing receipt receipt_key requires_date_confirmation resolution_attempted resolver reusable_routes route_attempted router search_area seen selection_counts text timing_counts token'.split()),
 'StopResolver':set('_alternatives _areas _audits _cache _excluded_regions _expires _named_only _observed _pages _paging _result _started _token discovery outing'.split()),
 'AdvancedRouter':set('_arguments _evidence _result all_candidates checked pending_paths resolver'.split()),
 'ProviderBudget':set('_active _details_window _elements _lookups _matrix_window _requests _search_window settings'.split()),
 'OutingBudget':set('_details _dispatched _elements _gross _matrix_requests _pagination _requests _searches _seen _session stop_reason'.split()),
 'PlacesDiscovery':{'outing'}}


def registry():
    # Module names are code constants, never supplied by a record or browser.
    types={}
    for name in MODULES:
        try:m=importlib.import_module('backend.'+name)
        except ModuleNotFoundError as e:
            if e.name=='backend.'+name:continue
            raise
        for n,t in vars(m).items():
            if isinstance(t,type) and t.__module__==m.__name__ and issubclass(t,(BaseModel,Enum)):
                types[m.__name__+'.'+n]=t
    return types


def factories():
    from backend.advanced_planning import Session
    from backend.stop_resolution import StopResolver
    from backend.advanced_routing import AdvancedRouter
    from backend.provider_budget import ProviderBudget,OutingBudget
    from backend.places import PlacesDiscovery
    return {t.__name__:t for t in (Session,StopResolver,AdvancedRouter,ProviderBudget,OutingBudget,PlacesDiscovery)}


class Graph:
    def __init__(self,now_ms):
        self.now_ms=now_ms;self.mono=monotonic();self.types=registry();self.native=factories();self.nodes=[];self.memo={};self.deadline=now_ms+600000;self.route_deadline=None
    def stamp(self,value):return int(self.now_ms+(value-self.mono)*1000)
    def unstamp(self,value):return self.mono+(value-self.now_ms)/1000
    def encode(self,v,depth=0):
        if depth>64 or len(self.nodes)>20000:raise Denied('native_graph_bound')
        if v is None or type(v) in (str,int,bool):return v
        if type(v) is float:
            if not math.isfinite(v):raise Denied('native_number')
            return v
        if isinstance(v,Enum):return {'enum':type(v).__module__+'.'+type(v).__name__,'value':v.value}
        if type(v) in (datetime,date,Decimal,UUID,HttpUrl):return {'scalar':type(v).__name__,'value':str(v)}
        if id(v) in self.memo:return {'ref':self.memo[id(v)]}
        n=len(self.nodes);self.memo[id(v)]=n;self.nodes.append(None)
        enc=lambda x:self.encode(x,depth+1)
        if isinstance(v,BaseModel):
            key=type(v).__module__+'.'+type(v).__name__
            if self.types.get(key) is not type(v):raise Denied('native_model:'+key)
            fields={k:getattr(v,k) for k in type(v).model_fields}
            # Published bearers are never restored as authority. Receipt records use hashes.
            for k in ('saveReceipt','saveAccessToken'):
                if k in fields:fields[k]=None
            from backend.routes import RouteLeg
            if type(v) is RouteLeg and v.status!='same_location':
                if v.observed_at is None or v.observed_at.utcoffset() is None:raise Denied('native_route_unknown')
                self.route_deadline=min(self.route_deadline or 10**16,int(v.observed_at.timestamp()*1000)+300000)
            row={'model':key,'fields':{k:enc(x) for k,x in fields.items()}}
        elif type(v) in (list,tuple,set):row={'sequence':type(v).__name__,'items':[enc(x) for x in v]}
        elif type(v) is dict:row={'pairs':[[enc(k),enc(x)] for k,x in v.items()]}
        elif type(v).__name__ in self.native and type(v) is self.native[type(v).__name__]:
            name=type(v).__name__;fields=dict(vars(v));fields.pop('lock',None);fields.pop('_lock',None)
            if name=='Session':fields['receipt']=None;fields['receipt_key']=None
            if name=='ProviderBudget':
                if fields.pop('cost',None) is not None or fields['_active']:raise Denied('native_active_or_ledger_budget')
            optional={'Session':{'reusable_routes'},'StopResolver':{'_named_only'}}.get(name,set())
            if set(fields)-FIELDS[name] or (FIELDS[name]-optional)-set(fields):raise Denied('native_unknown_field')
            for k in ('expires','_expires'):
                if k in fields:fields[k]={'nativeDeadline':self.stamp(fields[k])};self.deadline=min(self.deadline,fields[k]['nativeDeadline'])
            for k in ('_matrix_window','_search_window','_details_window'):
                if k in fields:fields[k]=[(self.stamp(t),u) for t,u in fields[k]] if k=='_matrix_window' else [self.stamp(t) for t in fields[k]]
            row={'native':name,'fields':{k:enc(x) for k,x in fields.items()}}
        else:raise Denied('native_nonserializable')
        self.nodes[n]=row;return {'ref':n}
    def dump(self,value):return {'root':self.encode(value),'nodes':self.nodes}
    def load(self,record):
        if type(record) is not dict or set(record)!={'root','nodes'} or type(record['nodes']) is not list or len(record['nodes'])>20000:raise Denied('native_graph')
        nodes=record['nodes'];memo={};busy=set()
        def dec(v,depth=0):
            if depth>64:raise Denied('native_graph_bound')
            if v is None or type(v) in (str,int,bool):return v
            if type(v) is float and math.isfinite(v):return v
            if type(v) is not dict:raise Denied('native_tag')
            if set(v)=={'scalar','value'}:
                f={'datetime':datetime.fromisoformat,'date':date.fromisoformat,'Decimal':Decimal,'UUID':UUID,'HttpUrl':HttpUrl}.get(v['scalar'])
                if f is None:raise Denied('native_scalar')
                return f(v['value'])
            if set(v)=={'enum','value'}:
                t=self.types.get(v['enum'])
                if t is None or not issubclass(t,Enum):raise Denied('native_enum')
                return t(v['value'])
            if set(v)!={'ref'} or type(v['ref']) is not int or not 0<=v['ref']<len(nodes):raise Denied('native_reference')
            n=v['ref']
            if n in memo:return memo[n]
            if n in busy:raise Denied('native_cycle')
            busy.add(n);r=nodes[n];child=lambda x:dec(x,depth+1)
            if type(r) is not dict:raise Denied('native_node')
            if set(r)=={'pairs'}:
                pairs=[(child(k),child(x)) for k,x in r['pairs']];out=dict(pairs)
                if len(out)!=len(pairs):raise Denied('native_duplicate_key')
            elif set(r)=={'sequence','items'}:
                f={'list':list,'tuple':tuple,'set':set}.get(r['sequence'])
                if f is None:raise Denied('native_sequence')
                out=f(child(x) for x in r['items'])
            elif set(r)=={'model','fields'}:
                t=self.types.get(r['model'])
                if t is None or not issubclass(t,BaseModel) or set(r['fields'])!=set(t.model_fields):raise Denied('native_model_schema')
                out=t.model_validate({k:child(x) for k,x in r['fields'].items()})
            elif set(r)=={'native','fields'}:
                name=r['native']
                if name not in self.native or set(r['fields'])-FIELDS[name]:raise Denied('native_factory')
                optional={'Session':{'reusable_routes'},'StopResolver':{'_named_only'}}.get(name,set())
                if (FIELDS[name]-optional)-set(r['fields']):raise Denied('native_missing_field')
                fields={k:child(x) for k,x in r['fields'].items()}
                for k in ('expires','_expires'):
                    if k in fields:fields[k]=self.unstamp(fields[k]['nativeDeadline'])
                for k in ('_matrix_window','_search_window','_details_window'):
                    if k in fields:fields[k]=[(self.unstamp(t),u) for t,u in fields[k]] if k=='_matrix_window' else [self.unstamp(t) for t in fields[k]]
                t=self.native[name]
                if name=='ProviderBudget':
                    if fields['settings'].exploration:raise Denied('native_ledger_not_portable')
                    out=t(fields['settings'])
                elif name=='OutingBudget':out=t(fields['_session'])
                elif name in ('PlacesDiscovery','StopResolver'):out=t(fields['outing'])
                elif name=='AdvancedRouter':out=t(fields['resolver'])
                else:out=t(fields['text'],fields['journey'],fields['context'],fields['outing']._session,limitation=fields['limitation'])
                for k,x in fields.items():setattr(out,k,x)
                if name=='ProviderBudget' and out._active:raise Denied('native_active_budget')
                if name=='Session':
                    if not isinstance(out.candidates,dict) or any(k!=out.route_id(c) for k,c in out.candidates.items()) or not out.seen<=set(out.candidates) or not out.current_ids<=out.seen:raise Denied('native_candidate_history')
                    if out.router is not None and out.router.resolver is not out.resolver:raise Denied('native_resolver_owner')
                if name in ('ProviderBudget','OutingBudget'):
                    for k in FIELDS[name]:
                        if k.startswith('_') and type(getattr(out,k,None)) is int and not 0<=getattr(out,k)<=10**12:raise Denied('native_budget_state')
            else:raise Denied('native_node')
            busy.remove(n);memo[n]=out;return out
        try:return dec(record['root'])
        except (ValueError,TypeError,KeyError,AttributeError,IndexError,OverflowError):raise Denied('native_incompatible_state') from None
