"""Dedicated public weather refresh: collect at T-18, target publication by T-15."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import time
ROOT=Path(__file__).resolve().parents[1];UTC=dt.timezone.utc

def stamp():return dt.datetime.now(UTC)
def parse(value):return dt.datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(UTC)
def read(path,default):
 try:return json.loads(path.read_text())
 except (OSError,ValueError):return default

def due_games(fixtures,audit,now):
 result=[]
 for g in fixtures:
  gid=g.get('game_id') or g.get('gameId');kickoff=g.get('kickoff')
  if not gid or not kickoff:continue
  when=parse(kickoff);old=audit.get(gid,{})
  if now<when<=now+dt.timedelta(minutes=35) and not (old.get('kickoff')==when.isoformat() and old.get('deadlineMet')):result.append({**g,'gameId':gid,'kickoff':when.isoformat()})
 return sorted(result,key=lambda g:g['kickoff'])

def refresh_result(game,forecast,collected,published):
 kickoff=parse(game['kickoff']);deadline=kickoff-dt.timedelta(minutes=15);retrieved=parse(forecast['retrievedAt']) if forecast.get('retrievedAt') else None
 fresh=forecast.get('status')=='ok' and retrieved is not None and kickoff-dt.timedelta(minutes=20)<=retrieved<=deadline and published-retrieved<=dt.timedelta(minutes=5)
 return {'gameId':game['gameId'],'kickoff':game['kickoff'],'targetAt':(kickoff-dt.timedelta(minutes=18)).isoformat(),'deadlineAt':deadline.isoformat(),'retrievedAt':forecast.get('retrievedAt'),'collectedAt':collected.isoformat(),'publishedAt':published.isoformat(),'deadlineMet':bool(fresh and published<=deadline),'status':'current' if fresh and published<=deadline else 'late_or_unavailable','reason':forecast.get('reason'),'provider':forecast.get('provider')}

def save_audit(rows):
 path=ROOT/'data/weather-kickoff-refresh.json';tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps({'generatedAt':stamp().isoformat(),'policy':'Checks every five minutes; collects at T−18 targeting publication by T−15. Provider and Actions delays can miss targets; actual timestamps are audited. Implications are recalculated from the retrieved hourly forecast, not invented stat penalties.','games':list(rows.values())},separators=(',',':')));tmp.replace(path)

def publish(message):
 for args in [['git','config','user.name','github-actions[bot]'],['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],['git','add','data/stadium-weather.json','data/weather-kickoff-refresh.json']]:subprocess.run(args,cwd=ROOT,check=True,capture_output=True)
 if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode==0:return stamp()
 for args in [['git','commit','-m',message+' [skip ci]'],['git','pull','--rebase','origin','main'],['git','push','origin','HEAD:main']]:subprocess.run(args,cwd=ROOT,check=True,capture_output=True)
 return stamp()

def run(plan=False):
 snapshot=read(ROOT/'data/weather-kickoff-refresh.json',{});audit={g['gameId']:g for g in snapshot.get('games',[])}
 fixtures={g.get('gameId'):g for g in read(ROOT/'data/stadium-weather.json',{}).get('games',[])}
 for g in read(ROOT/'data/upcoming-games.json',{}).get('games',[]):fixtures[g.get('game_id')]=g
 due=due_games(list(fixtures.values()),audit,stamp())
 if plan:
  if os.getenv('GITHUB_OUTPUT'):
   with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('due='+str(bool(due)).lower()+'\n')
  print(json.dumps({'due':[g['gameId'] for g in due]}));return
 from scripts.refresh_stadium_weather import run as collect
 while due:
  target=parse(due[0]['kickoff'])-dt.timedelta(minutes=18)
  while stamp()<target:time.sleep(min(30,(target-stamp()).total_seconds()))
  batch=[g for g in due if parse(g['kickoff'])-dt.timedelta(minutes=18)<=stamp()];due=[g for g in due if g not in batch]
  try:
   snapshot=collect([g['gameId'] for g in batch],resolve_venues=False);forecasts={g['gameId']:g for g in snapshot['games']}
  except Exception as error:forecasts={g['gameId']:{'status':'unavailable','reason':'Weather refresh failed: '+type(error).__name__} for g in batch}
  collected=stamp()
  for g in batch:audit[g['gameId']]={**refresh_result(g,forecasts.get(g['gameId'],{}),collected,collected),'publishedAt':None,'deadlineMet':False,'status':'publishing'}
  save_audit(audit);published=publish('Refresh stadium forecasts for the T-15 kickoff deadline')
  for g in batch:audit[g['gameId']]=refresh_result(g,forecasts.get(g['gameId'],{}),collected,published)
  save_audit(audit);publish('Record actual pregame weather publication timing')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',action='store_true');run(p.parse_args().plan)
