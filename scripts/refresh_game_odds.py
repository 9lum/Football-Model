"""Current NFL game markets from The Odds API. Never publishes credentials or re-dates quotes."""
import datetime as dt
import json
import math
import os
from pathlib import Path
from scripts.refresh_odds import fetch,number,read,ProviderError
from scripts.game_market_history import append_history
from scripts.odds_quota import routine_budget,kickoff_reserve,observe_quota,days_remaining
MARKETS=['h2h','spreads','totals']
UTC=dt.timezone.utc

def refresh_minutes(remaining,cost,override=None,now=None,policy=None):
    # Scheduled checks are free; paid game pulls use at most a paced share of surplus.
    surplus=max(0,remaining-kickoff_reserve(now,policy))
    required=max(15,math.ceil(days_remaining(now,policy)*24*60*cost/max(1,surplus*.1)))
    return max(required,number(override,15)) if override else required

def collect(output=Path('data'),key=None,now=None,force=False):
    output.mkdir(parents=True,exist_ok=True);now=now or dt.datetime.now(UTC);previous=read(output/'game-odds.json',{})
    due=previous.get('nextRefreshAt')
    if due and not force:
        try:
            if dt.datetime.fromisoformat(due.replace('Z','+00:00'))>now:
                print(json.dumps({'status':'not_due','nextRefreshAt':due}));return previous
        except ValueError:pass
    status={'schemaVersion':1,'generatedAt':now.isoformat(),'source':'The Odds API','status':'unavailable','data':[],'errors':[],'requestedMarkets':MARKETS,'collectionMode':'Server-collected snapshots, not streaming live odds. The browser reloads published prices every minute.'}
    key=key or os.environ.get('ODDS_API_KEY')
    try:
        if not key:raise ProviderError('missing_secret')
        _,quota=fetch('events',key);remaining=number(quota.get('remaining'),0);policy=observe_quota(output,quota,now,kind='games');status['monthlyQuotaPolicy']=policy;regions='us,us2' if remaining>=2000 else 'us';cost=3*len(regions.split(','));status.update(quota=quota,requestedRegions=regions)
        if remaining<cost:raise ProviderError('insufficient_quota')
        if ',' in regions and routine_budget(remaining,cost,now,policy,kind='games')<cost:
            regions='us';cost=3;status['requestedRegions']=regions
        if routine_budget(remaining,cost,now,policy,kind='games')<cost:raise ProviderError('reserved_for_kickoff')
        payload,quota=fetch('odds',key,regions=regions,markets=','.join(MARKETS),oddsFormat='american')
        observe_quota(output,quota,now,kind='games')
        if not isinstance(payload,list):raise ProviderError('schema')
        events=[]
        for event in payload:
            try:start=dt.datetime.fromisoformat(event['commence_time'].replace('Z','+00:00'))
            except (KeyError,ValueError):continue
            if not now-dt.timedelta(hours=6)<start<=now+dt.timedelta(days=8):continue
            if not isinstance(event.get('bookmakers'),list):continue
            events.append({**event,'collectedAt':now.isoformat()})
        events.sort(key=lambda e:e['commence_time']);remaining_after=number(quota.get('remaining'),max(0,remaining-cost));minutes=refresh_minutes(remaining_after,cost,os.environ.get('GAME_ODDS_REFRESH_MINUTES'),now,policy)
        count=sum(len(m.get('outcomes',[])) for e in events for b in e['bookmakers'] for m in b.get('markets',[]) if m.get('key') in MARKETS)
        status.update(status='ok' if count else 'no_prices',data=events,eventCount=len(events),quoteCount=count,books=sorted({b['title'] for e in events for b in e['bookmakers']}),quota=quota,estimatedCreditsUsed=number(quota.get('last'),cost),refreshMinutes=minutes,nextRefreshAt=(now+dt.timedelta(minutes=minutes)).isoformat(),refreshPolicy='Quota-aware by default. GAME_ODDS_REFRESH_MINUTES may slow the interval but cannot make it faster than monthly pacing.')
        if events:
            append_history(output,events,now.isoformat())
            path=output/'game-odds-history.json';history=read(path,{'snapshots':[]});history['snapshots'].append({'observedAt':now.isoformat(),'data':events});history['snapshots']=history['snapshots'][-96:]
            # Bound repository growth while retaining recent original observations.
            while len(json.dumps(history))>8_000_000 and len(history['snapshots'])>1:history['snapshots'].pop(0)
            path.write_text(json.dumps(history,separators=(',',':')))
    except ProviderError as error:
        status['errors'].append({'code':error.status})
        status['data']=[e for e in previous.get('data',[]) if dt.datetime.fromisoformat(e['commence_time'].replace('Z','+00:00'))>now-dt.timedelta(hours=6)]
        status['lastSuccessfulCollectionAt']=previous.get('lastSuccessfulCollectionAt',previous.get('generatedAt'))
    tmp=output/'game-odds.json.tmp';tmp.write_text(json.dumps(status,separators=(',',':')));tmp.replace(output/'game-odds.json')
    print(json.dumps({k:v for k,v in status.items() if k!='data'},indent=2));return status
if __name__=='__main__':collect(force=os.environ.get('FORCE_GAME_ODDS_REFRESH')=='1')
