"""Shared monthly sportsbook-credit policy. Provider balances remain authoritative."""
import datetime as dt,json,math,os
from pathlib import Path
UTC=dt.timezone.utc

def _date(value):
 try:return dt.datetime.fromisoformat(str(value).replace('Z','+00:00')).astimezone(UTC)
 except (ValueError,TypeError):return None

def _number(value):
 try:return max(0,int(value))
 except (ValueError,TypeError):return None

def days_remaining(now=None,policy=None):
 now=now or dt.datetime.now(UTC);end=_date((policy or {}).get('nextResetAt'))
 return max(1,math.ceil((end-now).total_seconds()/86400)) if end and end>now else 31

def remaining_games(now=None,policy=None):
 known=(policy or {}).get('remainingGames')
 return max(1,int(known)) if known is not None else 16*math.ceil(days_remaining(now,policy)/7)

def kickoff_reserve(now=None,policy=None):
 reserve=6*remaining_games(now,policy)
 try:reserve=max(reserve,int(os.environ.get('ODDS_KICKOFF_RESERVE_CREDITS',reserve)))
 except ValueError:pass
 return reserve

def routine_budget(remaining,requested,now=None,policy=None,kind='props'):
 # Keep six core yardage/TD markets for each remaining scheduled game.
 # Caps cannot be bypassed by a large per-run budget or refresh-frequency override.
 surplus=max(0,int(remaining)-kickoff_reserve(now,policy));share,checks={'props':(.6,4),'td':(.3,4),'games':(.1,1)}.get(kind,(.6,4))
 cap=math.floor(surplus*share/(days_remaining(now,policy)*checks))
 return max(0,min(int(requested),cap))

def observe_quota(output,quota,now=None,kind='props'):
 if kind not in ['props','td','games','kickoff']:raise ValueError('Unknown quota consumer')
 now=now or dt.datetime.now(UTC);output=Path(output);output.mkdir(exist_ok=True,parents=True);path=output/('odds-quota-'+kind+'.json')
 try:previous=json.loads(path.read_text())
 except (OSError,ValueError):previous={}
 remaining=_number(quota.get('remaining'));used=_number(quota.get('used'));old_used=_number(previous.get('reportedUsed'));old_remaining=_number(previous.get('reportedRemaining'))
 if previous.get('checkedAt')==now.isoformat() and used is not None and old_used is not None and used<old_used:return previous
 renewed=remaining is not None and old_remaining is not None and remaining>old_remaining and ((used is not None and old_used is not None and used<old_used) or old_remaining==0)
 configured=_date(os.environ.get('ODDS_API_RESET_AT'));end=configured if configured and configured>now else _date(previous.get('nextResetAt'))
 if renewed or not end or end<=now:end=now+dt.timedelta(days=31)
 ids={};latest=None
 for name in ['stadium-weather.json','upcoming-games.json']:
  try:rows=json.loads((output/name).read_text()).get('games',[])
  except (OSError,ValueError):continue
  for g in rows:
   kickoff=_date(g.get('kickoff'))
   if not kickoff:continue
   if latest is None or kickoff>latest:latest=kickoff
   if now<kickoff<=end:ids[g.get('gameId') or g.get('game_id') or g.get('id') or g.get('kickoff')]=kickoff
 known=len(ids) if latest and latest>=end else None
 result={'schemaVersion':1,'checkedAt':now.isoformat(),'reportedRemaining':remaining,'reportedUsed':used,'renewalDetected':renewed,'cycleStartObservedAt':now.isoformat() if renewed else previous.get('cycleStartObservedAt'),'nextResetAt':end.isoformat(),'resetDateSource':'configured' if configured and configured>now else 'conservative_31_day_estimate_not_provider_billing_date','remainingGames':known,'freePublicFallbacksEnabled':True,'policy':'Protect core pregame yardage and touchdown coverage across the remaining cycle. Routine previews use a capped share of surplus. Replenishment is detected from provider-reported balances; no replacement key or paid upgrade is automatic.'}
 result['protectedKickoffCredits']=kickoff_reserve(now,result)
 temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(result,separators=(',',':')));temporary.replace(path)
 return result
