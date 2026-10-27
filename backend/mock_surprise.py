"""Surprise selection over the shared fictional generator/evaluator/ranker."""
from backend.planner import generate_candidates
from backend.ranking import evaluate_candidate,score_candidates
from backend.models import RankingResult,PlanningError
from backend.surprise import select,record
from backend.option_sessions import option_sessions
from backend.places import DiscoveryError

def mock_surprise(request,context=None):
    context=context or {'request':request,'seen':set(),'usedPrimary':set(),'recent':set(request.recentSurpriseIds),'mockSurprise':True}
    generated=generate_candidates(request)
    if generated.errors:return RankingResult(request=request,message=generated.message,errors=generated.errors)
    evaluated=[evaluate_candidate(request,c) for c in generated.candidates if c.id not in context['seen']]
    ranked=score_candidates(request,[p for p in evaluated if p.feasibility!='violated'])
    plans=select(ranked,3,context);record(context,plans)
    if 'token' not in context:context['token']=option_sessions.create(context)
    return RankingResult(request=request,plans=[p for p in plans if p.feasibility=='confirmed'],provisionalPlans=[p for p in plans if p.feasibility=='provisional'],
        optionsToken=context['token'],canExpand=len(ranked)>len(plans),
        message=f'{len(plans)} fictional Surprise Me options. No real routes or venues were requested.' if plans else 'No more eligible fictional combinations in this outing.',
        errors=[] if plans else [PlanningError(code='no_availability',message='The fictional candidate pool is exhausted or cannot meet the limits.')],
        notes=['Surprise Me begins at the first activity. All venues, prices, travel and schedules are fictional. No first-leg journey is planned.'])

def more_mock_surprise(token):
    context,lock=option_sessions.get(token)
    if not context.get('mockSurprise'):raise DiscoveryError('mode_changed','This outing uses another data mode. Generate again.')
    if not lock.acquire(blocking=False):raise DiscoveryError('busy','Another options request is running.')
    try:
        from backend.date_resolution import resolve_datetime
        r=context['request']
        if resolve_datetime('',[],[],r.location,manual_date=r.date.isoformat()).issues:raise DiscoveryError('date_expired','Choose a future date and generate again.')
        return mock_surprise(context['request'],context)
    finally:lock.release()
