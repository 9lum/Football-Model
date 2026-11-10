"""Verified final ESPN offensive box scores bridging delayed weekly public-stat releases."""
import concurrent.futures as cf
import datetime as dt
import json,re
from pathlib import Path
from zoneinfo import ZoneInfo
from scripts.archive_matchup_research import fetch
from scripts.model_record import code,name
from scripts.performance_boxscore import player_stats,number
ROOT=Path(__file__).resolve().parents[1]
FIELDS={'passing':{'passingYards':'passing_yards','passingTouchdowns':'passing_tds','interceptions':'passing_interceptions'},'rushing':{'rushingAttempts':'carries','rushingYards':'rushing_yards','rushingTouchdowns':'rushing_tds'},'receiving':{'receptions':'receptions','receivingYards':'receiving_yards','receivingTouchdowns':'receiving_tds','receivingTargets':'targets'}}
def clean_id(v):return str(v).strip().removesuffix('.0') if v is not None else ''
def extract(summary):
 rows=player_stats(summary);by_key={(code(r['team']),r['espnId']):r for r in rows};checks=[]
 for t in summary.get('boxscore',{}).get('players',[]):
  club=code(t.get('team',{}).get('displayName'))
  for g in t.get('statistics',[]):
   kind=g.get('name');keys=g.get('keys',[])
   if kind not in FIELDS:continue
   team_totals=dict(zip(keys,g.get('totals',[])));parsed=[]
   for a in g.get('athletes',[]):
    key=(club,str(a.get('athlete',{}).get('id','')));row=by_key.get(key)
    if not row:continue
    row['position']=a.get('athlete',{}).get('position',{}).get('abbreviation');values=dict(zip(keys,a.get('stats',[])))
    if kind=='passing':
     pair=str(values.get('sacks-sackYardsLost','')).split('-')
     if len(pair)==2:
      for k,v in zip(['sacks_suffered','sack_yards_lost'],pair):
       n=number(v)
       if n is not None:row['stats'][k]=-abs(n) if k=='sack_yards_lost' else n
    parsed.append(row)
   mappings=dict(FIELDS[kind])
   if kind=='passing':mappings.update({'completions/passingAttempts:0':'completions','completions/passingAttempts:1':'attempts'})
   for source,target in mappings.items():
    if ':' in source:
     key,i=source.split(':');parts=str(team_totals.get(key,'')).split('/');expected=number(parts[int(i)]) if len(parts)==2 else None
    else:expected=number(team_totals.get(source))
    if expected is None:continue
    supplied=[r['stats'].get(target) for r in parsed];complete=all(v is not None for v in supplied)
    value=sum(supplied) if complete else None
    # ESPN passing team totals are NET; individual player passing yards are GROSS.
    if kind=='passing' and target=='passing_yards' and value is not None:
     losses=[r['stats'].get('sack_yards_lost') for r in parsed];value=value-sum(abs(v) for v in losses) if all(v is not None for v in losses) else None
    checks.append({'team':club,'stat':target,'playerSumAdjusted':value,'teamTotal':expected,'matches':value is not None and abs(value-expected)<.001})
 return rows,checks

def run(output=ROOT/'data',now=None):
 from edge.availability import public_csv
 now=now or dt.datetime.now(dt.timezone.utc);today=now.astimezone(ZoneInfo('America/New_York')).date();dates=[today-dt.timedelta(days=n) for n in range(3)];events={};errors=[]
 for day in dates:
  try:
   board=fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates='+day.strftime('%Y%m%d'))
   for e in board.get('events',[]):
    if e.get('status',{}).get('type',{}).get('completed'):events[e['id']]=e
  except Exception as ex:errors.append({'date':day.isoformat(),'error':type(ex).__name__})
 people=public_csv('players','players.csv.gz',ROOT/'work/actuals-reference-cache');ids={};positions={}
 for r in people.to_dict('records'):
  espn=clean_id(r.get('espn_id'));gsis=clean_id(r.get('gsis_id'))
  if re.fullmatch(r'\d+',espn) and re.fullmatch(r'00-\d+',gsis):ids.setdefault(espn,set()).add(gsis);positions[gsis]=r.get('position')
 # Public current roster crosswalk supplements missing new-player IDs without name guessing.
 latest=json.loads((output/'latest.json').read_text());roster=json.loads((output/'availability.json').read_text()).get('roster',[])
 for p in roster:
  espn=clean_id(p.get('espnId'))
  if re.fullmatch(r'\d+',espn):ids.setdefault(espn,set()).add(p['playerId']);positions[p['playerId']]=p['position']
 profiles={p['playerId']:p for p in latest.get('players',[])};known=[*latest.get('forecasts',[]),*[g for p in latest.get('players',[]) for g in p.get('history',[])]];rows=[];games=[];unmapped=[];checks=[]
 def load(e):
  try:return e,fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event='+e['id']),None
  except Exception as ex:return e,None,type(ex).__name__
 with cf.ThreadPoolExecutor(max_workers=4) as pool:
  for event,summary,error in pool.map(load,events.values()):
   if error:errors.append({'event':event['id'],'error':error});continue
   header=summary.get('header',{});comp=(header.get('competitions') or [{}])[0]
   if not comp.get('status',{}).get('type',{}).get('completed'):continue
   season=header.get('season',{});year=season.get('year');week_value=header.get('week');week=(week_value.get('number') if isinstance(week_value,dict) else week_value) or event.get('week',{}).get('number')
   if season.get('type') not in [None,2] or not year or not week:continue
   teams={c.get('homeAway'):c for c in comp.get('competitors',[])};home=code(teams['home']['team'].get('abbreviation'));away=code(teams['away']['team'].get('abbreviation'));kickoff=comp.get('date') or event['date'];gid=f'{year}_{int(week):02d}_{away}_{home}'
   candidates={g.get('gameId') for g in known if re.fullmatch(r'\d{4}_\d{2}_[A-Z]+_[A-Z]+',g.get('gameId','')) and code(g['gameId'].split('_')[2])==away and code(g['gameId'].split('_')[3])==home and g.get('kickoff') and abs((dt.datetime.fromisoformat(g['kickoff'].replace('Z','+00:00'))-dt.datetime.fromisoformat(kickoff.replace('Z','+00:00'))).total_seconds())<3600}
   if len(candidates)==1:gid=next(iter(candidates))
   scores={'id':'espn-'+event['id'],'gameId':gid,'season':year,'week':week,'homeTeam':home,'awayTeam':away,'kickoff':kickoff,'homeScore':number(teams['home'].get('score')),'awayScore':number(teams['away'].get('score')),'completed':True,'observedAt':now.isoformat()};games.append(scores)
   extracted,audit=extract(summary);checks.extend([{**c,'gameId':gid} for c in audit])
   for r in extracted:
    key=clean_id(r['espnId']);mapped=ids.get(key,set());club=code(r['team'])
    if len(mapped)!=1:unmapped.append({'gameId':gid,'name':r['name'],'espnId':key,'team':club,'representedBy':'espn-'+key})
    pid=next(iter(mapped)) if len(mapped)==1 else 'espn-'+key
    position=r.get('position') or positions.get(pid) or profiles.get(pid,{}).get('position');position=position if isinstance(position,str) and position.strip() else 'OFF'
    if position=='OFF':
     try:
      athlete=fetch('https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/'+key).get('athlete',{})
      if str(athlete.get('id'))==key:position=athlete.get('position',{}).get('abbreviation') or position
     except Exception:pass
    rows.append({'playerId':pid,'espnId':key,'identityNamespace':'gsis' if len(mapped)==1 else 'espn','name':r['name'],'position':position,'season':year,'week':week,'gameId':gid,'kickoff':kickoff,'team':club,'opponent':away if club==home else home,'basic':r['stats'],'completed':True,'observedAt':now.isoformat(),'source':'https://www.espn.com/nfl/boxscore/_/gameId/'+event['id']})
 old_path=output/'recent-player-actuals.json';old=json.loads(old_path.read_text()) if old_path.exists() else {};current={(r['gameId'],r['playerId']):r for r in old.get('rows',[]) if dt.datetime.fromisoformat(r['kickoff'].replace('Z','+00:00'))>=now-dt.timedelta(days=21)}
 for row in rows:
  for k,previous in list(current.items()):
   if previous.get('espnId')==row['espnId'] and previous['gameId']==row['gameId'] and previous['playerId']!=row['playerId']:del current[k]
 current.update({(r['gameId'],r['playerId']):r for r in rows});payload={'schemaVersion':1,'generatedAt':now.isoformat(),'checkedDates':[d.isoformat() for d in dates],'games':games,'rows':list(current.values()),'audit':{'finalGames':len(games),'playerGameRows':len(rows),'teamChecks':len(checks),'mismatches':[c for c in checks if not c['matches']],'unmappedPlayers':unmapped,'errors':errors},'scope':'Explicit completed-game ESPN box-score fields. Missing fields stay missing; DNP is not zero. Passing team net-yard totals are adjusted for sacks when validating gross player yards. Public corrections remain possible.'}
 directory=output/'player-research';directory.mkdir(parents=True,exist_ok=True)
 for pid in {r['playerId'] for r in payload['rows'] if r['identityNamespace']=='espn'}:
  own=[r for r in payload['rows'] if r['playerId']==pid];(directory/(pid+'.json')).write_text(json.dumps({'schemaVersion':1,'playerId':pid,'generatedAt':now.isoformat(),'games':own,'scope':'Explicit ESPN final box scores; provider ID retained until an unambiguous GSIS crosswalk is available.','sources':[{'dataset':'ESPN final box scores','status':'ok'}]},separators=(',',':')))
 output.mkdir(parents=True,exist_ok=True);old_path.write_text(json.dumps(payload,separators=(',',':'),allow_nan=False));print(json.dumps(payload['audit']));return payload
if __name__=='__main__':run()
