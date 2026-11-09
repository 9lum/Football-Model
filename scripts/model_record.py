"""Persistent fixed-rule review of authentic pregame snapshots, not a wager/ROI ledger."""
import datetime as dt
import json
import unicodedata
import re
from pathlib import Path
from scripts.game_market_history import instant,finite
UTC=dt.timezone.utc
NAMES={'ARI':'Arizona Cardinals','ATL':'Atlanta Falcons','BAL':'Baltimore Ravens','BUF':'Buffalo Bills','CAR':'Carolina Panthers','CHI':'Chicago Bears','CIN':'Cincinnati Bengals','CLE':'Cleveland Browns','DAL':'Dallas Cowboys','DEN':'Denver Broncos','DET':'Detroit Lions','GB':'Green Bay Packers','HOU':'Houston Texans','IND':'Indianapolis Colts','JAX':'Jacksonville Jaguars','KC':'Kansas City Chiefs','LAC':'Los Angeles Chargers','LAR':'Los Angeles Rams','LV':'Las Vegas Raiders','MIA':'Miami Dolphins','MIN':'Minnesota Vikings','NE':'New England Patriots','NO':'New Orleans Saints','NYG':'New York Giants','NYJ':'New York Jets','PHI':'Philadelphia Eagles','PIT':'Pittsburgh Steelers','SEA':'Seattle Seahawks','SF':'San Francisco 49ers','TB':'Tampa Bay Buccaneers','TEN':'Tennessee Titans','WAS':'Washington Commanders'}
def code(t):return {'LA':'LAR','WSH':'WAS','JAC':'JAX'}.get(t,next((k for k,v in NAMES.items() if v==t),t))
def name(t):
 s=unicodedata.normalize('NFKD',t or '').encode('ascii','ignore').decode().lower()
 return re.sub('[^a-z0-9]','',re.sub(r'\b(jr|sr|ii|iii|iv|v)\.?$','',s))
def read(path,default=None):
 try:return json.loads(path.read_text())
 except (OSError,ValueError):return {} if default is None else default

def same_game(p,r):
 a,b=instant(p.get('kickoff')),instant(r.get('kickoff'))
 return a is not None and b is not None and abs(a-b)<=21600 and code(p.get('homeTeam'))==code(r.get('homeTeam')) and code(p.get('awayTeam'))==code(r.get('awayTeam'))
def base(p,issued):
 parts=p['gameId'].split('_')
 return {'gameId':p['gameId'],'season':int(parts[0]),'week':int(parts[1]),'homeTeam':code(p['homeTeam']),'awayTeam':code(p['awayTeam']),'kickoff':p['kickoff'],'issuedAt':issued}
def valid_prior(p,issued):return instant(issued) is not None and instant(p.get('kickoff')) is not None and instant(issued)<instant(p['kickoff'])
def choose_total(p,observations):
 quotes=[]
 for q in observations:
  observed=instant(q.get('observedAt'));kickoff=instant(p['kickoff'])
  if q.get('market')!='totals' or q.get('side')!='Over' or not finite(q.get('point')) or observed is None or observed>=kickoff:continue
  if not same_game(p,q):continue
  # Use only quotes that were already recorded when this model snapshot was issued.
  if observed>instant(p['projectedAt']):continue
  quotes.append(q)
 priority=lambda q:0 if 'draftkings' in (q.get('bookKey') or '').lower() else 1 if 'fanduel' in (q.get('bookKey') or '').lower() else 2
 return min(quotes,key=lambda q:(priority(q),-instant(q['observedAt']),q.get('bookKey',''))) if quotes else None

def build_record(previous,history,td_reports,snapshot,movement,now):
 rows={r['id']:r for r in previous.get('rows',[])}
 for p in history.get('projections',[]):
  issued=p.get('projectedAt')
  if not valid_prior(p,issued):continue
  b=base(p,issued);gid=p['gameId'];old=rows.get('moneyline:'+gid)
  if not old or instant(now)<instant(p['kickoff']):
   pick=p['homeTeam'] if p.get('probHomeWin',0)>p.get('probAwayWin',0) else p['awayTeam'] if p.get('probAwayWin',0)>p.get('probHomeWin',0) else None
   rows['moneyline:'+gid]={**b,'id':'moneyline:'+gid,'market':'moneyline','pick':code(pick) if pick else 'No lean','side':code(pick) if pick else None,'projection':max(p.get('probHomeWin',0),p.get('probAwayWin',0)),'status':'pending'}
  key='total:'+gid;old=rows.get(key)
  if not old or instant(now)<instant(p['kickoff']) or old.get('line') is None:
   q=choose_total(p,movement.get('observations',[]));line=q['point'] if q else None
   side='Over' if line is not None and p['total']>line else 'Under' if line is not None and p['total']<line else None
   rows[key]={**b,'id':key,'market':'total','pick':(side+' '+str(line)) if side else 'No archived line' if line is None else 'No lean','side':side,'projection':p.get('total'),'line':line,'book':q.get('book') if q else None,'lineObservedAt':q.get('observedAt') if q else None,'status':'pending'}
 for report in td_reports:
  for g in report.get('games',[]):
   issued=g.get('pregameGeneratedAt') or report.get('generatedAt')
   if not valid_prior(g,issued):continue
   existing=[r for r in rows.values() if r['gameId']==g['gameId'] and r['market']=='touchdown']
   if existing and instant(now)>=instant(g['kickoff']):continue
   if existing:
    for r in existing:del rows[r['id']]
   pool=g.get('players') or g.get('candidates') or []
   for club in [g['awayTeam'],g['homeTeam']]:
    eligible=[p for p in pool if code(p.get('team'))==code(club) and finite(p.get('probability')) and not p.get('unavailable') and not (p.get('health') or {}).get('ruledOut') and str((p.get('health') or {}).get('status','')).upper() not in ['OUT','IR','PUP','NFI','INACTIVE','SUSPENDED']]
    seen=set()
    for p in sorted(eligible,key=lambda p:p['probability'],reverse=True):
     pid=p.get('playerId')
     if not pid or pid in seen:continue
     if len(seen)>=3:break
     seen.add(pid);key='touchdown:'+g['gameId']+':'+pid
     rows[key]={**base(g,issued),'id':key,'market':'touchdown','playerId':pid,'team':code(club),'pick':p['name'],'projection':p['probability'],'status':'pending'}
 for r in rows.values():
  matches=[s for s in snapshot.get('results',[]) if same_game(r,s) and s.get('completed') is True and all(finite(s.get(k)) for k in ['homeScore','awayScore'])]
  if len(matches)!=1:continue
  s=matches[0];r['settledAt']=s.get('observedAt');r['finalScore']=f"{r['awayTeam']} {s['awayScore']:g} – {r['homeTeam']} {s['homeScore']:g}"
  if r['market']=='moneyline':
   winner=r['homeTeam'] if s['homeScore']>s['awayScore'] else r['awayTeam'] if s['awayScore']>s['homeScore'] else None
   r.update(actual=winner or 'Tie',status='ungraded' if not r.get('side') else 'push' if not winner else 'win' if r['side']==winner else 'loss')
  elif r['market']=='total':
   actual=s['homeScore']+s['awayScore'];line=r.get('line')
   r.update(actual=actual,status='ungraded' if not r.get('side') or line is None else 'push' if actual==line else 'win' if (actual>line)==(r['side']=='Over') else 'loss')
  else:
   scorers=[p for p in s.get('scorers',[]) if code(p.get('team'))==r['team'] and name(p.get('name'))==name(r['pick'])]
   count=scorers[0].get('touchdowns') if len(scorers)==1 else None
   if finite(count) and count>0:r.update(actual=count,status='win')
   elif s.get('scorersComplete') and not scorers:r.update(actual=0,status='loss')
   else:r.update(actual=None,status='ungraded')
 return {'schemaVersion':1,'generatedAt':now,'rules':'Fixed-rule review of saved pregame forecasts, not logged wagers or ROI. Moneyline: higher predicted win probability. Total: model total vs DraftKings, then FanDuel, then another archived Over line already known at model issue time. TD: top three eligible scorers per team. Ties/pushes excluded from hit rate. Missing lines or scoring coverage remain ungraded.','rows':sorted(rows.values(),key=lambda r:(r['kickoff'],r['id']),reverse=True)}

def update_record(output=Path('data'),now=None):
 output=Path(output);stamp=now or dt.datetime.now(UTC).isoformat()
 value=build_record(read(output/'model-record.json'),read(output/'game-projection-history.json'),[read(output/'touchdown-research.json'),read(output/'touchdown-pregame-archive.json')],read(output/'public-game-odds.json'),read(output/'game-market-movement.json'),stamp)
 (output/'model-record.json').write_text(json.dumps(value,separators=(',',':'),allow_nan=False));return value
if __name__=='__main__':update_record()
