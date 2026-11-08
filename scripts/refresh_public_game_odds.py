"""Observe publicly listed ESPN game lines. Provider update times stay unknown when absent."""
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from scripts.refresh_odds import read
from scripts.game_market_history import append_history
UTC=dt.timezone.utc
SOURCE='https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard'
def numeric(value,line=False):
    if isinstance(value,str):
        value=value.strip()
        if line and value.upper() in ['PK','PICK']:return 0.
        if not line and value.upper() in ['EVEN','EV']:return 100
        if line:value=re.sub(r'^[oOuU]','',value)
    try:return float(value)
    except (TypeError,ValueError):return None

def parse(payload,observed,now):
    events=[]
    for event in payload.get('events',[]):
        state=event.get('status',{}).get('type',{})
        if state.get('completed'):continue
        try:start=dt.datetime.fromisoformat(event['date'].replace('Z','+00:00'))
        except (KeyError,ValueError):continue
        if not now-dt.timedelta(hours=6)<start<=now+dt.timedelta(days=8):continue
        for comp in event.get('competitions',[]):
            teams={c.get('homeAway'):c.get('team',{}).get('displayName') for c in comp.get('competitors',[])}
            if not teams.get('home') or not teams.get('away'):continue
            books=[]
            for odds in comp.get('odds',[]):
                provider=odds.get('provider',{});name=provider.get('displayName') or provider.get('name')
                if not name:continue
                markets=[]
                for source,key,sides in [('moneyline','h2h',['home','away']),('pointSpread','spreads',['home','away']),('total','totals',['over','under'])]:
                    outcomes=[]
                    for side in sides:
                        # ESPN's pregame 'close' field is its currently listed quote, not proof of a historical closing price.
                        quote=odds.get(source,{}).get(side,{}).get('close',{});price=numeric(quote.get('odds'))
                        point=numeric(quote.get('line'),True) if key!='h2h' else None
                        if price is None or abs(price)<100 or (key!='h2h' and point is None):continue
                        outcome={'name':teams[side] if side in teams else side.title(),'price':price}
                        if point is not None:outcome['point']=point
                        outcomes.append(outcome)
                    if outcomes:markets.append({'key':key,'last_update':None,'observed_at':observed,'outcomes':outcomes})
                if markets:books.append({'key':'espn-'+str(provider.get('id',name)),'title':name+' · ESPN','source':'ESPN public scoreboard','observed_at':observed,'last_update':None,'markets':markets})
            if books:events.append({'id':'espn-'+str(event['id']),'home_team':teams['home'],'away_team':teams['away'],'commence_time':event['date'],'collectedAt':observed,'source':'ESPN public scoreboard','gameStatus':state.get('description'),'bookmakers':books})
    return events

def parse_results(payload,observed):
    """Scores are final only when ESPN explicitly marks the event completed."""
    rows=[]
    for event in payload.get('events',[]):
        state=event.get('status',{}).get('type',{})
        for comp in event.get('competitions',[]):
            teams={c.get('homeAway'):c for c in comp.get('competitors',[])}
            if not all(teams.get(side,{}).get('team',{}).get('displayName') for side in ['home','away']):continue
            scores={side:numeric(teams[side].get('score')) for side in ['home','away']}
            valid=all(v is not None and v>=0 and v.is_integer() for v in scores.values())
            rows.append({'id':'espn-'+str(event['id']),'kickoff':event.get('date'),
                'homeTeam':teams['home']['team']['displayName'],'awayTeam':teams['away']['team']['displayName'],
                'homeScore':scores['home'],'awayScore':scores['away'],
                'completed':state.get('completed') is True and valid,'state':state.get('state'),
                'description':state.get('description'),'clock':event.get('status',{}).get('displayClock'),'period':event.get('status',{}).get('period'),'detail':state.get('shortDetail') or state.get('detail'),'observedAt':observed})
    return rows

def collect(output=Path('data'),now=None):
    now=now or dt.datetime.now(UTC);stamp=now.isoformat();games=read(output/'upcoming-games.json',{}).get('games',[]);weeks=sorted({(g['season'],g['week']) for g in games if g.get('game_type','REG')=='REG'})[:2]
    queries=[{'dates':year,'seasontype':2,'week':week} for year,week in weeks] or [{}];events={};results={};errors=[]
    for query in queries:
        try:
            with urlopen(Request(SOURCE+('?' + urlencode(query) if query else ''),headers={'User-Agent':'Projections-n-Shit/1.0'}),timeout=25) as r:payload=json.load(r)
            for event in parse(payload,stamp,now):events[event['id']]=event
            for result in parse_results(payload,stamp):results[result['id']]=result
        except Exception as error:errors.append({'source':'ESPN public scoreboard','code':getattr(error,'code',type(error).__name__)})
    old=read(output/'public-game-odds.json',{})
    prior={r['id']:r for r in old.get('results',[])};prior.update(results)
    retained=sorted(prior.values(),key=lambda r:r.get('kickoff') or '',reverse=True)[:128]
    value={'generatedAt':stamp,'source':'ESPN public scoreboard','status':'ok' if events else 'unavailable' if errors else 'no_prices','data':list(events.values()) if events or not errors else old.get('data',[]),'results':retained,'eventCount':len(events),'errors':errors,'nextRefreshAt':(now+dt.timedelta(minutes=15)).isoformat(),'limitations':['Publicly listed game lines, checked approximately every 15 minutes subject to GitHub delays. No streaming or provider-update-time guarantee.','Source quote-update timestamps are not supplied and remain null. observed_at records when this app read the listing.','The pregame close field is not treated as a verified archived closing line for CLV.']}
    if events:append_history(output,list(events.values()),stamp)
    output.mkdir(parents=True,exist_ok=True);(output/'public-game-odds.json').write_text(json.dumps(value,separators=(',',':')));print(json.dumps({k:v for k,v in value.items() if k!='data'}));return value
if __name__=='__main__':collect()
