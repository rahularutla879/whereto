"""Invented seven-day response fixtures, relative to the test observation date."""
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo

def fixture_hours(*,closed=False,zone='America/New_York',now=None):
 now=now or datetime.now(timezone.utc);first=now.astimezone(ZoneInfo(zone)).date()
 def endpoint(day,hour):return {'date':{'year':day.year,'month':day.month,'day':day.day},'day':(day.weekday()+1)%7,'hour':hour,'minute':0}
 return {'timeZone':{'id':zone},'currentOpeningHours':{'periods':[] if closed else [{'open':endpoint(first+timedelta(days=i),9),'close':endpoint(first+timedelta(days=i),22)} for i in range(7)],'specialDays':[{'date':{'year':first.year,'month':first.month,'day':first.day}}]},'regularOpeningHours':{'periods':[{'open':{'day':i,'hour':9,'minute':0},'close':{'day':i,'hour':22,'minute':0}} for i in range(7)],'weekdayDescriptions':['Monday: 9:00 AM–10:00 PM','Tuesday: 9:00 AM–10:00 PM','Wednesday: 9:00 AM–10:00 PM','Thursday: 9:00 AM–10:00 PM','Friday: 9:00 AM–10:00 PM','Saturday: 9:00 AM–10:00 PM','Sunday: 9:00 AM–10:00 PM']}}
