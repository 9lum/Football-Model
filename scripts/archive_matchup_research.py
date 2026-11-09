"""Retain real published pregame snapshots per game; never recreate old forecasts."""
import concurrent.futures as futures
import datetime as dt
import json,os,re,time
from pathlib import Path
from urllib.request import Request,urlopen
from scripts.nfl_teams import FULL_NAMES
REPO='9lum/Football-Model';RAW=f'https://raw.githubusercontent.com/{REPO}/'
def stamp(value):return dt.datetime.fromisoformat(value.replace('Z','+00:00'))
def fetch(url):
 headers={'User-Agent':'NFLMatchupArchive/1.0'}
 if url.startswith('https://api.github.com/') and os.environ.get('GITHUB_TOKEN'):headers['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
 for attempt in range(3):
  try:
   with urlopen(Request(url,headers=headers),timeout=45) as response:return json.load(response)
  except Exception:
   if attempt==2:raise
   time.sleep(attempt+1)
def raw(sha,name):return fetch(RAW+sha+'/data/'+name+'.json')
def eligible(snapshot,publication):
 result={}
 for f in snapshot.get('forecasts',[]):
  gid=f.get('gameId','')
  if re.fullmatch(r'\d{4}_\d{2}_[A-Z]+_[A-Z]+',gid) and f.get('kickoff') and stamp(publication['issuedAt'])<stamp(f['kickoff']):result.setdefault(gid,[]).append(f)
 return result
def matches(event,f):
 try:return event.get('home_team')==FULL_NAMES.get(f.get('homeTeam')) and event.get('away_team')==FULL_NAMES.get(f.get('awayTeam')) and abs((stamp(event['commence_time'])-stamp(f['kickoff'])).total_seconds())<3600
 except (KeyError,ValueError,TypeError):return False

def archive(output=Path('data'),limit=24):
 directory=output/'matchup-research';directory.mkdir(parents=True,exist_ok=True)
 index_path=output/'matchup-research-index.json';previous=json.loads(index_path.read_text()) if index_path.exists() else {};seen=set(previous.get('inspectedCommits',[]));processed=[]
 commits=fetch(f'https://api.github.com/repos/{REPO}/commits?path=data/latest.json&per_page={limit}')
 publications=[{'commit':c['sha'],'issuedAt':c['commit']['committer']['date']} for c in commits if c['sha'] not in seen]
 def load(p):
  try:return p,raw(p['commit'],'latest')
  except Exception as e:print('Snapshot unavailable:',p['commit'],type(e).__name__);return p,{}
 winners={}
 with futures.ThreadPoolExecutor(max_workers=4) as pool:
  for p,snapshot in pool.map(load,publications):
   if snapshot.get('schemaVersion'):processed.append(p['commit'])
   for gid,forecasts in eligible(snapshot,p).items():
    old=winners.get(gid)
    if not old or stamp(p['issuedAt'])>stamp(old[0]['issuedAt']):winners[gid]=(p,snapshot,forecasts)
 extras={}
 def load_extra(pair):
  sha,name=pair
  try:return pair,raw(sha,name)
  except Exception:return pair,{}
 pairs=[(sha,name) for sha in {w[0]['commit'] for w in winners.values()} for name in ['availability','game-odds','public-game-odds','odds','weather','game-projections','upcoming-games','attd-odds','public-td-odds','touchdown-research']]
 with futures.ThreadPoolExecutor(max_workers=6) as pool:extras=dict(pool.map(load_extra,pairs))
 for gid,(p,snapshot,forecasts) in winners.items():
  path=directory/(gid+'.json');old=json.loads(path.read_text()) if path.exists() else {}
  if old.get('issuedAt') and (stamp(old['issuedAt'])>stamp(p['issuedAt']) or stamp(old['issuedAt'])==stamp(p['issuedAt']) and old.get('schemaVersion',0)>=2):continue
  sha=p['commit'];ids={f['playerId'] for f in forecasts};f=forecasts[0];cutoff=stamp(f['kickoff'])
  events=[e for name in ['game-odds','public-game-odds'] for e in extras.get((sha,name),{}).get('data',[]) if matches(e,f)]
  odds=[e for e in extras.get((sha,'odds'),{}).get('data',[]) if matches(e,f)]
  availability=extras.get((sha,'availability'),{})
  if availability.get('generatedAt') and stamp(availability['generatedAt'])>=cutoff:availability={}
  payload={'schemaVersion':2,'gameId':gid,'kickoff':f['kickoff'],'issuedAt':p['issuedAt'],'sourceCommit':sha,'kind':'published_pregame','bundle':{'schemaVersion':snapshot.get('schemaVersion',3),'season':snapshot.get('season'),'generatedAt':snapshot.get('generatedAt'),'forecasts':forecasts,'players':[v for v in snapshot.get('players',[]) if v['playerId'] in ids]},'availability':availability,'gameEvents':events,'oddsEvents':odds,'weather':next((g for g in extras.get((sha,'weather'),{}).get('games',[]) if g.get('gameId')==gid),None),'gameProjection':next((g for g in extras.get((sha,'game-projections'),{}).get('projections',[]) if g.get('gameId')==gid),None),'tdSnapshot':{'data':[e for name in ['attd-odds','public-td-odds'] for e in extras.get((sha,name),{}).get('data',[]) if matches(e,f)]},'tdReport':{**{k:v for k,v in extras.get((sha,'touchdown-research'),{}).items() if k in ['generatedAt','orderMethodology']},'allPlayerOdds':{pid:v for pid,v in extras.get((sha,'touchdown-research'),{}).get('allPlayerOdds',{}).items() if v.get('gameId')==gid}},'game':next((g for g in extras.get((sha,'upcoming-games'),{}).get('games',[]) if g.get('game_id')==gid),{}),'gameModelReport':{k:v for k,v in extras.get((sha,'game-projections'),{}).items() if k in ['generatedAt','model','validation','drawsPerGame']},'scope':'Original committed pregame model, inputs and recorded prices. Archived prices are not live. No postgame forecast reconstruction.'}
  path.write_text(json.dumps(payload,separators=(',',':'),allow_nan=False))
 index=[]
 for path in sorted(directory.glob('*.json')):
  d=json.loads(path.read_text());index.append({k:d[k] for k in ['gameId','kickoff','issuedAt','sourceCommit']})
 (output/'matchup-research-index.json').write_text(json.dumps({'games':index,'inspectedCommits':list(dict.fromkeys([*processed,*previous.get('inspectedCommits',[])]))[:200],'scope':'Verified published pregame snapshots; retained after final.'},separators=(',',':')))
 print(json.dumps({'archivedGames':len(index),'inspectedPublications':len(publications)}))
if __name__=='__main__':archive()
