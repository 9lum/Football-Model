"""Supplement missing exact over/under markets; never turn ATTD into rushing/receiving TDs."""
import datetime as dt,json,os,time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from scripts.refresh_odds import MARKETS,merge_markets,read
TYPES={'passing_yards':'player_pass_yds','rushing_yards':'player_rush_yds','receiving_yards':'player_reception_yds','receptions':'player_receptions','rushing_attempts':'player_rush_attempts','passing_attempts':'player_pass_attempts','passing_completions':'player_pass_completions','passing_tds':'player_pass_tds','interceptions':'player_pass_interceptions','rushing_tds':'player_rush_tds','receiving_tds':'player_reception_tds'}
TYPES.update(rushing_touchdowns='player_rush_tds',receiving_touchdowns='player_reception_tds')
VENDORS={'draftkings':'DraftKings','fanduel':'FanDuel','betrivers':'BetRivers','caesars':'Caesars','fanatics':'Fanatics'}
def normalize(rows,players,event):
    books={}
    for r in rows:
        key=TYPES.get(r.get('prop_type'));person=players.get(r.get('player_id'));vendor=r.get('vendor');market=r.get('market',{})
        if not key or not person or vendor not in VENDORS or market.get('type')!='over_under':continue
        if person.get('team',{}).get('full_name') not in [event['home_team'],event['away_team']]:continue
        try:line=float(r['line_value']);date=dt.datetime.fromisoformat(r['updated_at'].replace('Z','+00:00'))
        except (KeyError,ValueError,TypeError):continue
        if not 0<=line<10000 or not date.tzinfo:continue
        book=books.setdefault(vendor,{'key':vendor,'title':VENDORS[vendor],'markets':{}});m=book['markets'].setdefault(key,{'key':key,'last_update':r['updated_at'],'source':'BALLDONTLIE','timestampType':'provider_refresh','outcomes':[]})
        name=(person.get('first_name','')+' '+person.get('last_name','')).strip()
        if not name:continue
        for side,field in [('Over','over_odds'),('Under','under_odds')]:
            price=market.get(field)
            if isinstance(price,(int,float)) and abs(price)>=100:m['outcomes'].append({'name':side,'description':name,'point':line,'price':price})
    return {**event,'bookmakers':[{**b,'markets':list(b['markets'].values())} for b in books.values()]}
def collect(output=Path('data'),key=None,now=None,pause=time.sleep):
    key=key or os.environ.get('BALLDLIE_API_KEY') or os.environ.get('BALLDONTLIE_API_KEY');now=now or dt.datetime.now(dt.timezone.utc)
    snapshot=read(output/'odds.json',{});meta={'provider':'BALLDONTLIE','observedAt':now.isoformat(),'status':'missing_secret' if not key else 'no_matching_games','events':0,'quotesAdded':0,'errors':[]}
    if not key:return meta
    cached=read(output/'balldontlie.json',{});games=cached.get('datasets',{}).get('games',{}).get('rows',[]);players={p['id']:p for p in cached.get('datasets',{}).get('players',{}).get('rows',[])}
    requests=0
    def fetch(endpoint,params):
        nonlocal requests
        if requests:pause(13)
        requests+=1
        url='https://api.balldontlie.io/nfl/v1/'+endpoint+'?'+urlencode(params,doseq=True)
        with urlopen(Request(url,headers={'Authorization':key,'User-Agent':'Projections-n-Shit/1.0'}),timeout=20) as response:return json.load(response)
    pending=[]
    try:
        if not games:
            bundle=read(output/'latest.json',{});upcoming=sorted([f for f in bundle.get('forecasts',[]) if dt.datetime.fromisoformat(f['kickoff'].replace('Z','+00:00'))>now],key=lambda f:f['kickoff'])
            if upcoming:games=fetch('games',{'seasons[]':bundle['season'],'weeks[]':int(upcoming[0]['gameId'].split('_')[1]),'per_page':100}).get('data',[])
        for event in snapshot.get('data',[]):
            start=dt.datetime.fromisoformat(event['commence_time'].replace('Z','+00:00'))
            if not now<start<=now+dt.timedelta(days=8):continue
            game=next((g for g in games if g.get('home_team',{}).get('full_name')==event['home_team'] and g.get('visitor_team',{}).get('full_name')==event['away_team'] and abs((dt.datetime.fromisoformat(g['date'].replace('Z','+00:00'))-start).total_seconds())<3600),None)
            if not game:continue
            rows=fetch('odds/player_props',{'game_id':game['id']}).get('data',[]);pending.append((event,rows));meta['events']+=1
        missing=sorted({r['player_id'] for _,rows in pending for r in rows if r.get('prop_type') in TYPES and r.get('player_id') not in players})
        for i in range(0,len(missing),100):
            for p in fetch('players',{'player_ids[]':missing[i:i+100],'per_page':100}).get('data',[]):players[p['id']]=p
        for event,rows in pending:
            normalized=normalize(rows,players,event);existing={b.get('key',b.get('title')):{m['key'] for m in b.get('markets',[]) if m.get('outcomes')} for b in event.get('bookmakers',[])}
            for b in normalized['bookmakers']:
                b['markets']=[m for m in b['markets'] if m['key'] not in existing.get(b['key'],set())]
                meta['quotesAdded']+=sum(len(m['outcomes']) for m in b['markets'])
            normalized['bookmakers']=[b for b in normalized['bookmakers'] if b['markets']]
            # Empty requested set adds only missing markets without removing primary-source quotes.
            merged=merge_markets(event,normalized,[]);event.update(merged)
        meta['status']='ok' if meta['quotesAdded'] else 'no_additional_prices'
    except HTTPError as e:meta.update(status='unavailable');meta['errors'].append({'code':e.code})
    except Exception as e:meta.update(status='unavailable');meta['errors'].append({'code':type(e).__name__})
    snapshot['secondarySource']=meta
    snapshot['marketCoverage']={market:{'events':sum(any(m.get('key')==market and m.get('outcomes') for b in e.get('bookmakers',[]) for m in b.get('markets',[])) for e in snapshot.get('data',[])),'books':sorted({b.get('title',b.get('key')) for e in snapshot.get('data',[]) for b in e.get('bookmakers',[]) if any(m.get('key')==market and m.get('outcomes') for m in b.get('markets',[]))})} for market in MARKETS}
    (output/'odds.json').write_text(json.dumps(snapshot,separators=(',',':')));print(json.dumps(meta));return meta
if __name__=='__main__':collect()
