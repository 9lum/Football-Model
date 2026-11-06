"""Observe publicly listed ESPN game lines. Provider update times stay unknown when absent."""
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from scripts.refresh_odds import read
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

def collect(output=Path('data'),now=None):
    now=now or dt.datetime.now(UTC);stamp=now.isoformat();games=read(output/'upcoming-games.json',{}).get('games',[]);weeks=sorted({(g['season'],g['week']) for g in games if g.get('game_type','REG')=='REG'})[:2]
    queries=[{'dates':year,'seasontype':2,'week':week} for year,week in weeks] or [{}];events={};errors=[]
    for query in queries:
        try:
            with urlopen(Request(SOURCE+('?' + urlencode(query) if query else ''),headers={'User-Agent':'Projections-n-Shit/1.0'}),timeout=25) as r:payload=json.load(r)
            for event in parse(payload,stamp,now):events[event['id']]=event
        except Exception as error:errors.append({'source':'ESPN public scoreboard','code':getattr(error,'code',type(error).__name__)})
    old=read(output/'public-game-odds.json',{})
    value={'generatedAt':stamp,'source':'ESPN public scoreboard','status':'ok' if events else 'unavailable' if errors else 'no_prices','data':list(events.values()) if events or not errors else old.get('data',[]),'eventCount':len(events),'errors':errors,'nextRefreshAt':(now+dt.timedelta(minutes=15)).isoformat(),'limitations':['Publicly listed game lines, checked approximately every 15 minutes subject to GitHub delays. No streaming or provider-update-time guarantee.','Source quote-update timestamps are not supplied and remain null. observed_at records when this app read the listing.','The pregame close field is not treated as a verified archived closing line for CLV.']}
    output.mkdir(parents=True,exist_ok=True);(output/'public-game-odds.json').write_text(json.dumps(value,separators=(',',':')));print(json.dumps({k:v for k,v in value.items() if k!='data'}));return value
if __name__=='__main__':collect()
