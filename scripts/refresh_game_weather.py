"""ESPN's reported game conditions supplement unavailable forecasts; never label them observations or forecasts."""
import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from intelligence.providers import request_json
ROOT=Path(__file__).resolve().parents[1];UTC=dt.timezone.utc

def number(value):return isinstance(value,(int,float)) and not isinstance(value,bool)
def parse_conditions(payload,game,retrieved):
 event=str(game.get('espn') or game.get('espnId') or '')
 competition=(payload.get('header',{}).get('competitions') or [{}])[0]
 aliases={'LA':'LAR','WSH':'WAS'};code=lambda x:aliases.get(x,x)
 clubs={code(c.get('team',{}).get('abbreviation')) for c in competition.get('competitors',[])}
 expected={code(game.get('home_team') or game.get('homeTeam')),code(game.get('away_team') or game.get('awayTeam'))}
 if not event or str(competition.get('id'))!=event or clubs!=expected:return None
 w=payload.get('gameInfo',{}).get('weather') or {};temp=w.get('temperature');gust=w.get('gust')
 if not w or not (number(temp) or number(gust) or w.get('conditionId')):return None
 return {'gameId':game.get('game_id') or game['gameId'],'kickoff':game['kickoff'],'homeTeam':game.get('home_team') or game.get('homeTeam'),'awayTeam':game.get('away_team') or game.get('awayTeam'),
  'status':'ok','kind':'reported_game_conditions','provider':'ESPN / AccuWeather','source':f'https://www.espn.com/nfl/game/_/gameId/{event}',
  'observedAt':None,'retrievedAt':retrieved.isoformat(),'conditionText':w.get('conditionId'),'temperatureC':(temp-32)*5/9 if number(temp) else None,
  'gustKph':gust*1.609344 if number(gust) else None,'windKph':None,'precipitationMm':None,'precipitationProbability':None,'snowfallCm':None,
  'sourceUnits':'ESPN U.S. game-weather fields: temperature Fahrenheit; gust mph. Sustained wind and precipitation units are not verified and are not inferred.',
  'completed':competition.get('status',{}).get('type',{}).get('completed') is True}

def run():
 now=dt.datetime.now(UTC);snapshot=json.loads((ROOT/'data/upcoming-games.json').read_text());games=[]
 for g in snapshot.get('games',[]):
  try:k=dt.datetime.fromisoformat(g['kickoff'].replace('Z','+00:00'))
  except (KeyError,ValueError):continue
  if k-dt.timedelta(minutes=35)<=now<=k+dt.timedelta(hours=6) and (g.get('espn') or g.get('espnId')):games.append(g)
 path=ROOT/'data/game-weather.json'
 try:previous=json.loads(path.read_text());rows={g['gameId']:g for g in previous.get('games',[])}
 except (OSError,ValueError):rows={}
 def collect(g):
  event=g.get('espn') or g.get('espnId')
  try:return parse_conditions(request_json('https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary',{'event':event}),g,dt.datetime.now(UTC))
  except Exception:return None
 with ThreadPoolExecutor(max_workers=4) as pool:
  for row in pool.map(collect,games):
   if row:rows[row['gameId']]=row
 data={'generatedAt':dt.datetime.now(UTC).isoformat(),'games':list(rows.values()),'scope':'Provider-reported game conditions, not a measured station observation or a pregame forecast. Source measurement time is unavailable; retrieval time is recorded. Missing measurements stay null.'}
 tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(data,separators=(',',':'),allow_nan=False));tmp.replace(path);print(json.dumps({'eligibleGames':len(games),'reportedGames':len(rows)}))
if __name__=='__main__':run()
