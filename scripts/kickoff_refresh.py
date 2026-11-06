"""Deadline-aware final pregame snapshots. UTC targets; source timestamps stay original."""
import argparse,concurrent.futures,datetime as dt,gzip,hashlib,io,json,os,subprocess,time
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request,urlopen
from scripts.refresh_odds import fetch,read,number,ProviderError
UTC=dt.timezone.utc;ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';MARKETS=['player_anytime_td','player_1st_td','player_last_td','h2h','spreads','totals']
def stamp():return dt.datetime.now(UTC)
def parse(value):return dt.datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(UTC)
def save(name,payload):
 path=DATA/name;tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(payload,separators=(',',':'),allow_nan=False));tmp.replace(path)
def games():return read(DATA/'touchdown-research.json',{}).get('games',[])
def plan(now=None):
 now=now or stamp();old=read(DATA/'kickoff-refresh.json',{});prior={g['gameId']:g for g in old.get('games',[])};rows=[]
 for game in games():
  kickoff=parse(game['kickoff']);row={**prior.get(game['gameId'],{}),'gameId':game['gameId'],'kickoff':game['kickoff'],'targetAt':(kickoff-dt.timedelta(minutes=6,seconds=30)).isoformat(),'deadlineAt':(kickoff-dt.timedelta(minutes=5)).isoformat()}
  row.setdefault('status','started_without_final_snapshot' if kickoff<=now else 'scheduled');rows.append(row)
 return {'generatedAt':now.isoformat(),'policy':'Worker checks every five minutes, starts within 45 minutes of kickoff, prepares analysis early, and targets final odds at T−6m30s for publication by T−5m. Actions/provider delays and source/quota gaps can miss the deadline; source times and actual publication are recorded.','games':rows}
def due_games(payload,now=None):
 now=now or stamp();return [g for g in payload['games'] if now<parse(g['kickoff'])<=now+dt.timedelta(minutes=45) and not g.get('publishedAt')]
def wait_until(target):
 while stamp()<target:time.sleep(min(30,max(.05,(target-stamp()).total_seconds())))
def source_checks(season):
 base='https://github.com/nflverse/nflverse-data/releases/download/';urls={'playerStats':base+f'stats_player/stats_player_week_{season}.csv.gz','playByPlay':base+f'pbp/play_by_play_{season}.parquet','depthCharts':base+f'depth_charts/depth_charts_{season}.csv.gz','trades':'https://raw.githubusercontent.com/nflverse/nfldata/master/data/trades.csv'}
 def check(item):
  name,url=item
  try:
   with urlopen(Request(url,headers={'User-Agent':'Projections-n-Shit pregame source audit'}),timeout=12) as response:raw=response.read();return name,{'checkedAt':stamp().isoformat(),'sourceModifiedAt':response.headers.get('Last-Modified'),'sha256':hashlib.sha256(raw).hexdigest(),'status':'ok'}
  except Exception as error:return name,{'checkedAt':stamp().isoformat(),'status':'unavailable','error':type(error).__name__}
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:return dict(pool.map(check,urls.items()))
def sources_unchanged(before,after):return bool(before) and set(before)==set(after) and all(v.get('status')=='ok' and before.get(k,{}).get('sha256')==v.get('sha256') for k,v in after.items())
def refresh_availability(batch):
 import pandas as pd
 from edge.availability import parse_espn,parse_official,latest_depth,match_and_resolve,roster_roles,TEAM_SITES
 clubs={t for g in batch for t in [g['homeTeam'],g['awayTeam']]};bundle=read(DATA/'latest.json',{});previous=read(DATA/'availability.json',{});season=bundle['season'];week=int(batch[0]['gameId'].split('_')[1]);depth=previous.get('roster',[]);sources=[];records=[];now=pd.Timestamp.now(tz='UTC')
 def fetch_public(url):
  with urlopen(Request(url,headers={'User-Agent':'Projections-n-Shit/1.0'}),timeout=8) as r:return r.read()
 try:raw=fetch_public(f'https://github.com/nflverse/nflverse-data/releases/download/depth_charts/depth_charts_{season}.csv.gz');depth=latest_depth(pd.read_csv(io.BytesIO(gzip.decompress(raw)),low_memory=False),now)
 except Exception as error:sources.append({'source':'depth charts','status':'unavailable','error':type(error).__name__})
 jobs=[('espn','https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries')]+[(club,'https://www.'+TEAM_SITES[club]+'/team/injury-report/') for club in clubs if club in TEAM_SITES]
 def one(item):
  club,url=item
  try:
   raw=fetch_public(url);observed=stamp().isoformat();rows=parse_espn(json.loads(raw),season,week,observed) if club=='espn' else parse_official(raw.decode(),url,season,week,observed);return [r for r in rows if r['team'] in clubs],{'url':url,'status':'ok','observedAt':observed,'records':len(rows)}
  except Exception as error:return [],{'url':url,'status':'unavailable','error':type(error).__name__}
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
  for rows,source in pool.map(one,jobs):records.extend(rows);sources.append(source)
 injuries,_=match_and_resolve(records,depth,bundle.get('players',[]),season,week,now);merged={**previous.get('injuries',{}),**injuries};roles=roster_roles(depth,merged);previous.update(injuries=merged,roster=roles);previous.setdefault('kickoffChecks',{}).update({club:{'checkedAt':stamp().isoformat(),'sources':sources} for club in clubs});save('availability.json',previous);return {'checkedAt':stamp().isoformat(),'matchedPlayers':len(injuries),'sources':sources}
def merge_event(previous,event,market_keys):
 result={k:v for k,v in event.items() if k!='bookmakers'};by_key={b.get('key',b.get('title')):b for b in previous.get('bookmakers',[])}
 for b in event.get('bookmakers',[]):
  key=b.get('key',b.get('title'));old=by_key.get(key,{});markets={m['key']:{**m,**({'last_update':old['last_update']} if not m.get('last_update') and old.get('last_update') else {})} for m in old.get('markets',[]) if m.get('key') in market_keys}
  for m in b.get('markets',[]):
   if m.get('key') in market_keys:markets[m['key']]=m
  by_key[key]={**old,**b,'markets':list(markets.values())}
 result['bookmakers']=[{**b,'markets':[m for m in b.get('markets',[]) if m.get('key') in market_keys]} for b in by_key.values()];return result

def collect_final(batch,key=None,now=None):
 from scripts.nfl_teams import FULL_NAMES
 now=now or stamp();key=key or os.environ.get('ODDS_API_KEY');result={g['gameId']:{'status':'unavailable','markets':MARKETS} for g in batch}
 if not key:return {k:{**v,'error':'missing_secret'} for k,v in result.items()}
 try:events,quota=fetch('events',key)
 except ProviderError as error:return {k:{**v,'error':error.status} for k,v in result.items()}
 remaining=number(quota.get('remaining'),0);td=read(DATA/'attd-odds.json',{});gm=read(DATA/'game-odds.json',{});td_events={e['id']:e for e in td.get('data',[])};gm_events={e['id']:e for e in gm.get('data',[])}
 jobs=[]
 for g in sorted(batch,key=lambda g:g['kickoff']):
  event=next((e for e in events if e.get('home_team')==FULL_NAMES.get(g['homeTeam']) and e.get('away_team')==FULL_NAMES.get(g['awayTeam']) and abs((parse(e['commence_time'])-parse(g['kickoff'])).total_seconds())<3600),None)
  if not event:result[g['gameId']]['error']='no_matched_event';continue
  if parse(g['kickoff'])<=stamp():result[g['gameId']]['error']='kickoff_passed';continue
  if remaining<len(MARKETS):result[g['gameId']]['error']='insufficient_quota';continue
  remaining-=len(MARKETS);jobs.append((g,event))
 def request_one(job):
  g,event=job
  try:
   payload,q=fetch('events/'+event['id']+'/odds',key,timeout=8,regions='us',markets=','.join(MARKETS),oddsFormat='american');return g,event,payload,q,None
  except ProviderError as error:return g,event,None,None,error.status
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  for g,event,payload,q,error in pool.map(request_one,jobs):
   if error:result[g['gameId']]['error']=error;continue
   observed=stamp().isoformat();payload['collectedAt']=observed
   td_events[event['id']]=merge_event(td_events.get(event['id'],{}),payload,MARKETS[:3]);gm_events[event['id']]=merge_event(gm_events.get(event['id'],{}),payload,MARKETS[3:]);seen={m['key'] for b in payload.get('bookmakers',[]) for m in b.get('markets',[]) if m.get('outcomes')};times=[m.get('last_update') or b.get('last_update') for b in payload.get('bookmakers',[]) for m in b.get('markets',[]) if m.get('outcomes')];source_current=bool(times) and all(t and 0<=(stamp()-parse(t)).total_seconds()<=180 for t in times)
   result[g['gameId']]={'status':'collected' if set(MARKETS).issubset(seen) else 'partial','fetchedAt':observed,'sourceQuotesCurrent':source_current,'markets':sorted(seen),'missingMarkets':sorted(set(MARKETS)-seen),'providerTimestamps':sorted({t for t in times if t}),'remainingCredits':number(q.get('remaining'),remaining),'regions':'us'}
 td.update(data=list(td_events.values()),lastKickoffCheckAt=stamp().isoformat(),kickoffQuota=remaining);gm.update(data=list(gm_events.values()),lastKickoffCheckAt=stamp().isoformat());
 if any(v.get('fetchedAt') for v in result.values()):td['lastKickoffCollectionAt']=stamp().isoformat();gm['lastKickoffCollectionAt']=stamp().isoformat()
 save('attd-odds.json',td);save('game-odds.json',gm);return result

def reprice(batch,checks):
 import pandas as pd
 from edge.touchdowns import matched_quotes,game_context,write_markdown
 report=read(DATA/'touchdown-research.json',{});availability=read(DATA/'availability.json',{});td=read(DATA/'attd-odds.json',{});gm=read(DATA/'game-odds.json',{});health=availability.get('injuries',{});ids={g['gameId'] for g in batch};now=pd.Timestamp.now(tz='UTC')
 for g in report.get('games',[]):
  if g['gameId'] not in ids:continue
  game=SimpleNamespace(home_team=g['homeTeam'],away_team=g['awayTeam'],kickoff=pd.Timestamp(g['kickoff']));players=[]
  for p in g.get('players',[]):
   h=health.get(p['playerId'],{});
   if h.get('ruledOut'):
    if p['playerId'] in report.get('allPlayerOdds',{}):report['allPlayerOdds'][p['playerId']].update(markets={},status='unavailable',reason='Ruled out; no participation-conditional odds offered')
    continue
   p['health']={'label':h.get('label','Availability unconfirmed'),'confirmed':h.get('confirmed',False),'reviewRequired':h.get('reviewRequired',False)};p['quotes']=matched_quotes(p,game,td,now,p['probability'],report['validation'],h)
   if not checks.get('statisticsUnchanged'):
    entry=report.get('allPlayerOdds',{}).get(p['playerId'],{})
    entry['reason']='Statistics revision or source check requires refreshed analysis'
    for estimate in entry.get('markets',{}).values():estimate.update(validationPassed=False,status='requires refreshed analysis')
    for q in p['quotes']:q['qualified']=False;q['flags'].append('statistics revision or source check requires analysis refresh')
   players.append(p)
  ranked=sorted(players,key=lambda p:p['probability'],reverse=True);chosen=[{**ranked[0],'risk':'Core research · highest estimated probability'}] if ranked else [];value=sorted([p for p in ranked if p['probability']>=.1 and p['recent'].get('rzOpportunities',0)>=2 and p.get('quotes') and p['quotes'][0]['estimatedReturn']>0 and (not chosen or p['playerId']!=chosen[0]['playerId'])],key=lambda p:p['quotes'][0]['estimatedReturn'],reverse=True)
  if value:chosen.append({**value[0],'risk':'High-yield research · positive price estimate'})
  for p in ranked:
   if len(chosen)>=3:break
   if not any(v['playerId']==p['playerId'] for v in chosen):chosen.append({**p,'risk':'Additional research candidate'})
  g.update(players=ranked,candidates=chosen,context=game_context(game,gm),pricesUpdatedAt=stamp().isoformat(),pregameChecks=checks)
 save('touchdown-research.json',report);write_markdown(report,DATA/'touchdown-research.md')
def publish(message):
 if os.environ.get('PREGAME_PUBLISH')!='1':return None
 for args in [['git','config','user.name','github-actions[bot]'],['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],['git','add','data/kickoff-refresh.json','data/touchdown-research.json','data/touchdown-research.md','data/availability.json','data/attd-odds.json','data/game-odds.json']]:subprocess.run(args,cwd=ROOT,check=True,capture_output=True)
 if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode==0:return stamp()
 subprocess.run(['git','commit','-m',message+' [skip ci]'],cwd=ROOT,check=True,capture_output=True);subprocess.run(['git','pull','--rebase','-X','theirs','origin','main'],cwd=ROOT,check=True,capture_output=True);subprocess.run(['git','push','origin','HEAD:main'],cwd=ROOT,check=True,capture_output=True);return stamp()
def run():
 payload=plan();due=due_games(payload)
 if not due:print('No upcoming kickoff requires a worker.');return
 kickoff=min(parse(g['kickoff']) for g in due);report_games={g['gameId']:g for g in games()};batch=[report_games[g['gameId']] for g in due if parse(g['kickoff'])==kickoff];season=int(batch[0]['gameId'][:4]);wait_until(kickoff-dt.timedelta(minutes=26));print('Preparing current public statistics and availability for '+str(len(batch))+' games',flush=True)
 from edge.touchdowns import report
 refresh_availability(batch);before=source_checks(season);report();baseline=source_checks(season);stable=sources_unchanged(before,baseline);prepared=stamp().isoformat()
 wait_until(kickoff-dt.timedelta(minutes=9));health=refresh_availability(batch);final_sources=source_checks(season);unchanged=stable and sources_unchanged(baseline,final_sources);wait_until(kickoff-dt.timedelta(minutes=6,seconds=30));quotes=collect_final(batch);checks={'preparedAt':prepared,'availability':health,'statisticsCheckedAt':stamp().isoformat(),'statisticsUnchanged':unchanged,'statisticsSources':final_sources};reprice(batch,checks);payload=plan()
 for row in payload['games']:
  if row['gameId'] in quotes:row.update(status='publication_pending',odds=quotes[row['gameId']],**checks,publicationStartedAt=stamp().isoformat())
 save('kickoff-refresh.json',payload);published=publish('Publish final pregame TD and game-market snapshots')
 if published:
  for row in payload['games']:
   if row['gameId'] in quotes:row.update(publishedAt=published.isoformat(),deadlineMet=published<=parse(row['deadlineAt']),status='completed' if quotes[row['gameId']]['status']=='collected' and quotes[row['gameId']].get('sourceQuotesCurrent') and unchanged else 'partial')
  save('kickoff-refresh.json',payload);publish('Record actual final pregame publication timing')
 print(json.dumps({'games':[g['gameId'] for g in batch],'publishedAt':published.isoformat() if published else None,'statisticsUnchanged':unchanged},indent=2))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--plan',action='store_true');parser.add_argument('--run',action='store_true');args=parser.parse_args()
 if args.run:run()
 else:
  payload=plan();save('kickoff-refresh.json',payload);due=bool(due_games(payload));print(json.dumps({'due':due,'games':len(payload['games'])}));
  if os.environ.get('GITHUB_OUTPUT'):
   with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('due='+str(due).lower()+'\n')
