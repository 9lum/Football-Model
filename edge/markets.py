"""Exact-event, exact-line pricing and conservative research gates."""
from datetime import datetime, timezone
import math
import numpy as np

FULL_NAMES={
'ARI':'Arizona Cardinals','ATL':'Atlanta Falcons','BAL':'Baltimore Ravens','BUF':'Buffalo Bills',
'CAR':'Carolina Panthers','CHI':'Chicago Bears','CIN':'Cincinnati Bengals','CLE':'Cleveland Browns',
'DAL':'Dallas Cowboys','DEN':'Denver Broncos','DET':'Detroit Lions','GB':'Green Bay Packers',
'HOU':'Houston Texans','IND':'Indianapolis Colts','JAX':'Jacksonville Jaguars','KC':'Kansas City Chiefs',
'LAC':'Los Angeles Chargers','LAR':'Los Angeles Rams','LV':'Las Vegas Raiders','MIA':'Miami Dolphins',
'MIN':'Minnesota Vikings','NE':'New England Patriots','NO':'New Orleans Saints','NYG':'New York Giants',
'NYJ':'New York Jets','PHI':'Philadelphia Eagles','PIT':'Pittsburgh Steelers','SEA':'Seattle Seahawks',
'SF':'San Francisco 49ers','TB':'Tampa Bay Buccaneers','TEN':'Tennessee Titans','WAS':'Washington Commanders'}
from .config import MARKET_SPECS
MARKETS={k:v[2] for k,v in MARKET_SPECS.items()}
def normalize_market(key):return 'player_reception_yds' if key=='player_receiving_yards' else key

def decimal(price):
    if not math.isfinite(price) or abs(price)<100:raise ValueError('Invalid American odds')
    return 1+price/100 if price>0 else 1+100/-price

def probability(samples,line,side,index=None):
    s=np.asarray(samples)
    if index is not None:s=s[:,index]
    win=float(np.mean(s>line if side=='Over' else s<line));push=float(np.mean(s==line))
    return win,push,1-win-push

def price(win,push,odds):return win*(decimal(odds)-1)-(1-win-push)

def market_values(f,key):
    if key in f.get('marketSamples',{}):return f['marketSamples'][key]['values']
    index={'player_reception_yds':0,'player_receptions':1}.get(key)
    return [r[index] for r in f.get('samples',[])] if index is not None else []

def scan(bundle,events,now=None):
    now=now or datetime.now(timezone.utc);rows=[]
    if not isinstance(events,list):events=[events]
    for event in events:
        kickoff=datetime.fromisoformat(event['commence_time'].replace('Z','+00:00'))
        matched=[f for f in bundle['forecasts'] if FULL_NAMES.get(f['homeTeam'])==event.get('home_team') and FULL_NAMES.get(f['awayTeam'])==event.get('away_team') and abs((datetime.fromisoformat(f['kickoff'])-kickoff).total_seconds())<3600]
        for book in event.get('bookmakers',[]):
            for market in book.get('markets',[]):
                key=normalize_market(market['key'])
                if key not in MARKET_SPECS:continue
                label,family,target=MARKET_SPECS[key]
                stamp=market.get('last_update',book.get('last_update'))
                try:age=(now-datetime.fromisoformat(stamp.replace('Z','+00:00'))).total_seconds()
                except (ValueError,TypeError,AttributeError):age=float('inf')
                for outcome in market.get('outcomes',[]):
                    side=outcome.get('name');line=outcome.get('point');odds=outcome.get('price')
                    if side not in ['Over','Under'] or not isinstance(line,(int,float)) or not math.isfinite(line):continue
                    try:decimal(odds)
                    except (ValueError,TypeError):continue
                    players=[f for f in matched if f['name'].casefold()==str(outcome.get('description','')).casefold()]
                    if len(players)!=1:continue
                    f=players[0];values=market_values(f,key)
                    if not len(values):continue
                    win,push,loss=probability(values,line,side);ev=price(win,push,odds)
                    opposite=next((o for o in market['outcomes'] if o.get('description')==outcome.get('description') and o.get('point')==line and o.get('name') in ['Over','Under'] and o.get('name')!=side),None)
                    nv=None
                    if opposite:
                        try:
                            a,b=1/decimal(odds),1/decimal(opposite['price']);nv=a/(a+b)
                        except (TypeError,ValueError):pass
                    report=bundle.get('familyValidation',{}).get(family,bundle['validation']).get('aggregate',{}).get(target,{})
                    reliability=[r for r in report.get('reliability',[]) if r['n']>=50]
                    gap=max([abs(r['predicted']-r['observed']) for r in reliability],default=.15)
                    haircut=gap+1.96*math.sqrt(win*(1-win)/len(values));lower=max(0,win-haircut)
                    conservative=price(lower,push,odds);route=f.get('routeScenario',{});route_ev=None
                    route_index={'player_reception_yds':0,'player_receptions':1}.get(key)
                    if route_index is not None and route.get('samples'):
                        rw,rp,_=probability(route['samples'],line,side,route_index);route_ev=price(rw,rp,odds)
                    passed=f.get('marketSamples',{}).get(key,{}).get('validationPassed',bundle.get('validationPassed',False))
                    flags=[]
                    if not 0<=age<=180:flags.append('stale odds')
                    if kickoff<=now:flags.append('in-play unsupported')
                    if not f.get('availabilityConfirmed',False):flags.append('availability unconfirmed')
                    if not passed:flags.append('validation gate failed')
                    generated=datetime.fromisoformat(bundle['generatedAt'])
                    if not 0<=(now-generated).total_seconds()<=172800:flags.append('stale model')
                    if route_index is not None:
                        if route_ev is None:flags.append('route scenario unavailable')
                        elif route_ev<=0:flags.append('route disagreement')
                    if book.get('key')=='manual' or book.get('manual'):flags.append('manual price unverified')
                    rows.append({'player':f['name'],'playerId':f['playerId'],'position':f.get('position'),'team':f.get('team'),'opponent':f.get('opponent'),
                        'gameId':f['gameId'],'book':book['title'],'market':key,'side':side,'line':line,'odds':odds,
                        'modelProbability':win,'pushProbability':push,'noVigProbability':nv,'estimatedEv':ev,
                        'conservativeEv':conservative,'routeScenarioEv':route_ev,'calibrationHaircut':haircut,
                        'flags':flags,'candidate':not flags and conservative>=.03})
    return sorted(rows,key=lambda r:r['conservativeEv'],reverse=True)
