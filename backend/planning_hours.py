"""Pure dated hours projection. Missing arrival/duration never becomes an open claim."""
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from backend.feasibility import _local_instant,_hours,EvidenceStop


def typical_hours(venue,day):
 regular=venue.regularOpeningHours
 if not regular or regular.periods is None:return None
 windows=[];target=((day.weekday()+1)%7)*1440
 for period in regular.periods:
  a,b=period.open,period.close
  if a.truncated or (b and b.truncated):return None
  if b is None:
   return [{'start':0,'end':1440}] if len(regular.periods)==1 and (a.day,a.hour,a.minute)==(0,0,0) else None
  begin=a.day*1440+a.hour*60+a.minute;finish=b.day*1440+b.hour*60+b.minute
  if finish<=begin:finish+=10080
  for shift in (-10080,0,10080):
   lo,hi=begin+shift-target,finish+shift-target
   if lo<1440 and hi>0:windows.append({'start':lo,'end':hi})
 return windows


def venue_hours(venue,day,*,start=None,end=None,evaluated_at=None,arrival=None,departure=None,calendar_timezone=None):
 now=evaluated_at or datetime.now(timezone.utc)
 result={'date':day.isoformat(),'timezone':venue.timeZone.id if venue.timeZone else None,
         'basis':'unavailable','status':'unverified','periods':[],
         'weekly':list((venue.regularOpeningHours.weekdayDescriptions if venue.regularOpeningHours else None) or []),
         'message':'Hours unverified.'}
 typical=typical_hours(venue,day)
 result.update(typicalPeriods=typical or [],typicalClosed=(not typical) if typical is not None else None)
 current=venue.currentOpeningHours
 stamp=venue.observedAt.get('currentOpeningHours.periods')
 if not venue.timeZone or not current or current.periods is None or not stamp:return result
 zone=ZoneInfo(venue.timeZone.id);first=stamp.astimezone(zone).date()
 if stamp>now or first!=now.astimezone(zone).date() or not first<=day<first+timedelta(days=7):return result
 lower=_local_instant(day,0,0,zone);upper=_local_instant(day+timedelta(days=1),0,0,zone)
 if lower is None or upper is None:return result
 coverage_lower=_local_instant(first,0,0,zone);coverage_upper=_local_instant(first+timedelta(days=7),0,0,zone)
 if coverage_lower is None or coverage_upper is None:return result
 intervals=[]
 for period in current.periods:
  a,b=period.open,period.close
  if b is None:
   if len(current.periods)==1 and (a.day,a.hour,a.minute,a.date,a.truncated) in ((0,0,0,None,None),(0,0,0,None,False)):
    intervals=[(lower,upper)];break
   return result
  if a.date is None or b.date is None or a.truncated or b.truncated:return result
  begin=_local_instant(a.date,a.hour,a.minute,zone);finish=_local_instant(b.date,b.hour,b.minute,zone)
  if begin is None or finish is None or begin>=finish or begin<coverage_lower or finish>coverage_upper:return result
  if begin<upper and finish>lower:intervals.append((begin,finish))
 result.update(basis='current',observedAt=stamp.isoformat(),specialDay=day in (current.specialDays or []))
 for begin,finish in intervals:
  local_a,local_b=begin.astimezone(zone),finish.astimezone(zone)
  result['periods'].append({'start':(local_a.date()-day).days*1440+local_a.hour*60+local_a.minute,
                             'end':(local_b.date()-day).days*1440+local_b.hour*60+local_b.minute})
 if calendar_timezone and calendar_timezone!=venue.timeZone.id:
  result['message']='Venue-local hours shown; the outing timezone differs, so visit compatibility is unverified.'
  return result
 # These are bounds on the whole outing, not invented arrival/departure times.
 low=lower if start is None else _local_instant(day,start//60,start%60,zone)
 high=upper if end is None or end==1440 else _local_instant(day,end//60,end%60,zone)
 if low is None or high is None:return {**result,'message':'Hours unverified for this clock window.'}
 if not any(a<high and b>low for a,b in intervals):
  result.update(status='closed',message='Closed throughout the requested window.' if start is not None or end is not None else 'Closed on the requested date.')
 else:result['message']='Date-specific hours; arrival and activity availability are unverified.'
 if arrival is not None and departure is not None:
  state,_,_=_hours(EvidenceStop(venue=venue,arrival=arrival,departure=departure,hours_request_date=first),now)
  if state=='feasible':result.update(status='open',message='Open during planned visit; reservations and activity sessions are unverified.')
  elif state=='infeasible':result.update(status='closed',message='Closed during part or all of the planned visit.')
 return result
