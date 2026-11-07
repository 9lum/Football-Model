"""Publish credential-free pregame odds snapshots; the API key never leaves Actions."""
import datetime as dt
import json
import math
import os
from pathlib import Path
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError

try:
    from scripts.odds_quota import routine_budget,kickoff_reserve
except ModuleNotFoundError:
    from odds_quota import routine_budget,kickoff_reserve

BASE='https://api.the-odds-api.com/v4/sports/americanfootball_nfl/'
MARKETS=['player_pass_yds','player_rush_yds','player_reception_yds','player_receptions','player_rush_attempts','player_pass_attempts','player_pass_completions','player_pass_tds','player_pass_interceptions','player_rush_tds','player_reception_tds']
class ProviderError(Exception):
    def __init__(self,status):self.status=status

def fetch(path,key,timeout=30,**params):
    url=BASE+path+'?'+urlencode({'apiKey':key,**params})
    try:
        with urlopen(Request(url,headers={'User-Agent':'Projections-n-Shit/1.0'}),timeout=timeout) as r:
            return json.load(r),{k:r.headers.get('x-requests-'+k) for k in ['remaining','used','last']}
    except HTTPError as e:raise ProviderError(e.code) from None
    except Exception:raise ProviderError('network') from None

def number(value,default):
    try:return max(0,int(float(value)))
    except (ValueError,TypeError,OverflowError):return default

def request_plan(remaining,override=None,slot=0):
    # Four refreshes/day, spreading reported remaining credits over roughly 30 days.
    budget=min(120,number(override,math.floor(remaining*.8/120)))
    budget=min(budget,remaining)
    regions='us,us2' if budget>=22 else 'us'
    markets=MARKETS if budget>=11 else MARKETS[:3] if budget>=3 else [MARKETS[slot%len(MARKETS)]]
    cost=len(markets)*len(regions.split(','))
    return budget,markets,regions,cost

def merge_markets(previous,fresh,requested):
    """Replace requested markets, preserve unrequested markets with original source times."""
    if previous and any(previous.get(k)!=fresh.get(k) for k in ['id','home_team','away_team','commence_time']):previous={}
    books={b.get('key',b.get('title')):b for b in previous.get('bookmakers',[])}
    incoming={b.get('key',b.get('title')):b for b in fresh.get('bookmakers',[])}
    result=[]
    for key in dict.fromkeys([*books,*incoming]):
        old=books.get(key,{});new=incoming.get(key,{})
        markets={m['key']:{**m,**({'last_update':old['last_update']} if not m.get('last_update') and old.get('last_update') else {})} for m in old.get('markets',[]) if m.get('key') not in requested}
        for m in new.get('markets',[]):
            markets[m['key']]={**m,**({'last_update':new['last_update']} if not m.get('last_update') and new.get('last_update') else {})}
        if markets:result.append({**old,**new,'last_update':old.get('last_update') if old else new.get('last_update'),'markets':list(markets.values())})
    return {**previous,**fresh,'bookmakers':result}

def needs_coverage(event,now):
    try:
        last=dt.datetime.fromisoformat(event.get('coverageAttemptedAt','').replace('Z','+00:00'))
        if 0<=(now-last).total_seconds()<7*86400:return False
    except (ValueError,TypeError):pass
    seen={m.get('key') for b in event.get('bookmakers',[]) for m in b.get('markets',[]) if m.get('outcomes')}
    return not set(MARKETS).issubset(seen)

def read(path,default):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return default

def collect(output=Path('data'),key=None,now=None):
    output.mkdir(parents=True,exist_ok=True);now=now or dt.datetime.now(dt.timezone.utc)
    previous=read(output/'odds.json',{});history=read(output/'odds-history.json',{'snapshots':[]})
    stamp=now.isoformat();status={'generatedAt':stamp,'source':'The Odds API','status':'unavailable','data':[], 'errors':[], 'cadence':'Scheduled every six hours; GitHub may delay runs. Browser checks snapshots every five minutes.'}
    key=key or os.environ.get('ODDS_API_KEY')
    try:
        if not key:raise ProviderError('missing_secret')
        events,quota=fetch('events',key)
        remaining=number(quota.get('remaining'),0)
        budget,markets,regions,cost=request_plan(remaining,os.environ.get('ODDS_REFRESH_CREDIT_BUDGET'),int(now.timestamp()//21600))
        budget=routine_budget(remaining,budget,now)
        status.update(quota=quota,creditBudget=budget,kickoffReservedCredits=kickoff_reserve(now),requestedMarkets=markets,requestedRegions=regions)
        model=read(output/'latest.json',{});names={'ARI':'Arizona Cardinals','ATL':'Atlanta Falcons','BAL':'Baltimore Ravens','BUF':'Buffalo Bills','CAR':'Carolina Panthers','CHI':'Chicago Bears','CIN':'Cincinnati Bengals','CLE':'Cleveland Browns','DAL':'Dallas Cowboys','DEN':'Denver Broncos','DET':'Detroit Lions','GB':'Green Bay Packers','HOU':'Houston Texans','IND':'Indianapolis Colts','JAX':'Jacksonville Jaguars','KC':'Kansas City Chiefs','LAC':'Los Angeles Chargers','LAR':'Los Angeles Rams','LV':'Las Vegas Raiders','MIA':'Miami Dolphins','MIN':'Minnesota Vikings','NE':'New England Patriots','NO':'New Orleans Saints','NYG':'New York Giants','NYJ':'New York Jets','PHI':'Philadelphia Eagles','PIT':'Pittsburgh Steelers','SEA':'Seattle Seahawks','SF':'San Francisco 49ers','TB':'Tampa Bay Buccaneers','TEN':'Tennessee Titans','WAS':'Washington Commanders'}
        modeled={(names.get(f.get('homeTeam')),names.get(f.get('awayTeam'))) for f in model.get('forecasts',[])}
        prior={e['id']:e for e in previous.get('data',[]) if isinstance(e,dict) and e.get('id')}
        eligible=[]
        for e in events:
            start=dt.datetime.fromisoformat(e['commence_time'].replace('Z','+00:00'))
            if now<start<=now+dt.timedelta(days=8) and (not modeled or (e['home_team'],e['away_team']) in modeled):eligible.append(e)
        eligible.sort(key=lambda e:(prior.get(e['id'],{}).get('collectedAt',''),e['commence_time']))
        # A bounded coverage pass prioritizes all prop markets once per game/week.
        # Keep 112 credits for one full NFL slate of six final-kickoff markets + buffer.
        coverage=any(needs_coverage(prior.get(e['id'],{}),now) for e in eligible)
        if coverage:
            reserve=min(kickoff_reserve(now),112)
            budget=min(176,max(0,remaining-reserve));markets=MARKETS;regions='us';cost=len(markets)
            status.update(creditBudget=budget,kickoffReservedCredits=reserve,requestedMarkets=markets,requestedRegions=regions,collectionMode='market_coverage',quotaPolicy='Bounded full-market coverage pass; retain 112 credits for final pregame pulls. Seven-day per-event retry cooldown.')
            eligible.sort(key=lambda e:(not needs_coverage(prior.get(e['id'],{}),now),e['commence_time']))
        if budget<cost:raise ProviderError('quota_budget')
        fresh=[];spent=0;requests=0
        for e in eligible:
            if coverage and not needs_coverage(prior.get(e['id'],{}),now):continue
            if requests>=(16 if coverage else 8) or spent+cost>budget:break
            requests+=1
            try:
                odds,q=fetch('events/'+quote(e['id'],safe='')+'/odds',key,regions=regions,markets=','.join(markets),oddsFormat='american')
                spent+=number(q.get('last'),cost);status['quota']=q
                if not isinstance(odds.get('bookmakers'),list):raise ProviderError('schema')
                odds['collectedAt']=stamp
                if coverage:odds['coverageAttemptedAt']=stamp
                fresh.append(odds)
                # A new response replaces that event; never relabel old quotes as fresh.
                prior[e['id']]=merge_markets(prior.get(e['id'],{}),odds,markets)
            except ProviderError as err:
                status['errors'].append({'eventId':e['id'],'code':err.status})
                spent+=cost
                if err.status in [401,403,429]:break
        valid={e['id'] for e in eligible};status['data']=[e for k,e in prior.items() if k in valid]
        quotes=sum(len(m.get('outcomes',[])) for e in fresh for b in e['bookmakers'] for m in b.get('markets',[]))
        status.update(status='ok' if quotes else 'no_prices' if fresh else 'unavailable',freshEvents=len(fresh),quoteCount=quotes,estimatedCreditsUsed=spent,eligibleEvents=len(eligible),books=sorted({b['title'] for e in fresh for b in e['bookmakers']}))
        status['marketCoverage']={market:{'events':sum(any(m.get('key')==market and m.get('outcomes') for b in e.get('bookmakers',[]) for m in b.get('markets',[])) for e in status['data']),'books':sorted({b.get('title',b.get('key')) for e in status['data'] for b in e.get('bookmakers',[]) if any(m.get('key')==market and m.get('outcomes') for m in b.get('markets',[]))})} for market in MARKETS}
        if fresh:history['snapshots'].append({'observedAt':stamp,'data':fresh})
    except ProviderError as err:
        status['errors'].append({'code':err.status})
        status['data']=[e for e in previous.get('data',[]) if dt.datetime.fromisoformat(e['commence_time'].replace('Z','+00:00'))>now]
    history['snapshots']=history.get('snapshots',[])[-28:]
    (output/'odds.json').write_text(json.dumps(status,separators=(',',':')))
    (output/'odds-history.json').write_text(json.dumps(history,separators=(',',':')))
    print(json.dumps({k:v for k,v in status.items() if k not in ['data']},indent=2))
    return status
if __name__=='__main__':collect()
