"""Freeze one available player-prop line while both forecast and price are pregame."""
from datetime import datetime
from copy import deepcopy
from .markets import FULL_NAMES

def stamp(value):
 try:return datetime.fromisoformat(str(value).replace('Z','+00:00')).timestamp()
 except (ValueError,TypeError):return None

def attach_benchmarks(ledger,odds,now):
 rows=deepcopy(ledger);observed=stamp(odds.get('generatedAt'));current=now.timestamp()
 if observed is None or not 0<=current-observed<=86400:return rows
 for row in rows:
  kickoff=stamp(row.get('kickoff'));issued=stamp(row.get('issuedAt'))
  if row.get('benchmark') or kickoff is None or issued is None or not issued<=current<kickoff or observed>=kickoff:continue
  parts=row['gameId'].split('_');away=FULL_NAMES.get({'LA':'LAR','WSH':'WAS'}.get(parts[2],parts[2]));home=FULL_NAMES.get({'LA':'LAR','WSH':'WAS'}.get(parts[3],parts[3]));choices=[]
  for event in odds.get('data',[]):
   if event.get('home_team')!=home or event.get('away_team')!=away or stamp(event.get('commence_time')) is None or abs(stamp(event['commence_time'])-kickoff)>=3600:continue
   for book in event.get('bookmakers',[]):
    for market in book.get('markets',[]):
     if market.get('key')!=row['market']:continue
     matched=[q for q in market.get('outcomes',[]) if str(q.get('description','')).lower()==row['player'].lower() and q.get('name') in ['Over','Under'] and isinstance(q.get('point'),(int,float))]
     points=set(q['point'] for q in matched)
     if len(points)!=1:continue
     rank=0 if 'draftkings' in book.get('key','') else 1 if 'fanduel' in book.get('key','') else 2
     choices.append((rank,book.get('key',''),{'line':next(iter(points)),'book':book.get('title'),'observedAt':odds['generatedAt'],'recordedAt':now.isoformat()}))
  if choices:row['benchmark']=sorted(choices,key=lambda q:q[:2])[0][2]
 return rows
