"""Bounded current-week odds recovery. Preserve kickoff reserve and original book timestamps."""
import datetime as dt
import json
import os
from pathlib import Path
from urllib.parse import quote
from scripts.refresh_odds import fetch,read,number,merge_markets,ProviderError
from scripts.odds_quota import kickoff_reserve,routine_budget
from scripts.refresh_game_odds import collect as collect_game_odds
CORE=['player_pass_yds','player_rush_yds','player_reception_yds']

def planned_requests(events,remaining,now,cap=55):
 budget=routine_budget(remaining,cap,now);tasks=[]
 # One all-game game-odds request costs three credits and is handled separately.
 spent=3
 for markets in [['player_anytime_td'],CORE]:
  for e in sorted(events,key=lambda e:e['commence_time']):
   if spent+len(markets)>budget:break
   tasks.append((e,markets));spent+=len(markets)
 return tasks

def run(output=Path('data'),key=None,now=None):
 key=key or os.environ.get('ODDS_API_KEY');now=now or dt.datetime.now(dt.timezone.utc)
 if not key:raise RuntimeError('Missing ODDS_API_KEY')
 events,q=fetch('events',key);latest_quota=q;remaining=number(q.get('remaining'),0);initial=remaining
 events=[e for e in events if now<dt.datetime.fromisoformat(e['commence_time'].replace('Z','+00:00'))<=now+dt.timedelta(days=8)]
 fixtures=read(output/'upcoming-games.json',{});active=min((int(g['week']) for g in fixtures.get('games',[]) if g.get('kickoff') and dt.datetime.fromisoformat(g['kickoff'].replace('Z','+00:00'))>now),default=None)
 if active is not None:
  starts={dt.datetime.fromisoformat(g['kickoff'].replace('Z','+00:00')) for g in fixtures.get('games',[]) if int(g.get('week',0))==active and g.get('kickoff')}
  events=[e for e in events if dt.datetime.fromisoformat(e['commence_time'].replace('Z','+00:00')) in starts]
 tasks=planned_requests(events,remaining,now)
 # Every collector queries the provider allowance; there is no assumed unlimited quota.
 game_report=collect_game_odds(output,key,now,force=True);latest_quota=game_report.get('quota') or latest_quota;remaining=number(latest_quota.get('remaining'),remaining)
 props=read(output/'odds.json',{});td=read(output/'attd-odds.json',{});pmap={e['id']:e for e in props.get('data',[])};tmap={e['id']:e for e in td.get('data',[])};fresh={'props':0,'touchdowns':0};errors=[];spent=initial-remaining
 for e,markets in tasks:
  cost=len(markets)
  if routine_budget(remaining,cost,now)<cost or spent+cost>55:break
  try:
   response,quota=fetch('events/'+quote(e['id'],safe='')+'/odds',key,regions='us',markets=','.join(markets),oddsFormat='american')
   latest_quota=quota;remaining=number(quota.get('remaining'),remaining-cost);spent=initial-remaining
   if not isinstance(response.get('bookmakers'),list):raise ProviderError('schema')
   response['collectedAt']=dt.datetime.now(dt.timezone.utc).isoformat();target=tmap if markets==['player_anytime_td'] else pmap;kind='touchdowns' if target is tmap else 'props'
   target[e['id']]=merge_markets(target.get(e['id'],{}),response,markets);fresh[kind]+=1
  except ProviderError as error:
   errors.append({'eventId':e['id'],'code':error.status});remaining-=cost;spent+=cost
   if error.status in [401,403,422,429]:break
 stamp=dt.datetime.now(dt.timezone.utc).isoformat()
 for filename,snapshot,data,kind in [('odds.json',props,pmap,'props'),('attd-odds.json',td,tmap,'touchdowns')]:
  snapshot.update(generatedAt=stamp,data=list(data.values()),status='ok' if fresh[kind] else snapshot.get('status','quota_wait'),quota={**latest_quota,'remaining':str(remaining)},freshEvents=fresh[kind],creditBudget=55,errors=errors,requestedMarkets=CORE if kind=='props' else ['player_anytime_td'],recovery={'capCredits':55,'creditsUsed':spent,'kickoffReservedCredits':kickoff_reserve(now),'refreshedEvents':fresh[kind],'requestedMarkets':CORE if kind=='props' else ['player_anytime_td'],'errors':errors})
  if kind=='touchdowns':snapshot.update(pricedEvents=sum(any(m.get('key')=='player_anytime_td' and m.get('outcomes') for b in e.get('bookmakers',[]) for m in b.get('markets',[])) for e in data.values()),quoteCount=sum(len(m.get('outcomes',[])) for e in data.values() for b in e.get('bookmakers',[]) for m in b.get('markets',[]) if m.get('key')=='player_anytime_td'))
  tmp=output/(filename+'.tmp');tmp.write_text(json.dumps(snapshot,separators=(',',':')));tmp.replace(output/filename)
 print(json.dumps({'eligibleEvents':len(events),'freshEvents':fresh,'creditsUsed':spent,'remaining':remaining,'reserved':kickoff_reserve(now),'errors':errors}))
if __name__=='__main__':run()
