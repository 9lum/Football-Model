"""Download public nflreadpy data and entitled supplemental providers into a real data lake."""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import math
import os
import re
from pathlib import Path
from .providers import collect_bdl,collect_weather

ROOT=Path(__file__).resolve().parents[1]
def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,default=str,separators=(',',':'),allow_nan=False))

def safe(value):
    if isinstance(value,dict):return {k:safe(v) for k,v in value.items()}
    if isinstance(value,list):return [safe(v) for v in value]
    if isinstance(value,float) and not math.isfinite(value):return None
    return value

def run(season=None,output=None,lake=None):
    now=dt.datetime.now(dt.timezone.utc);season=season or (now.year if now.month>=3 else now.year-1);output=output or ROOT/'data';lake=lake or ROOT/'work/lake';lake.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('NFLREADPY_CACHE','filesystem');os.environ.setdefault('NFLREADPY_CACHE_DIR',str(ROOT/'work/nflreadpy-cache'));os.environ.setdefault('NFLREADPY_TIMEOUT','45')
    import nflreadpy as nfl
    import polars as pl
    specs=[('player_stats',lambda:nfl.load_player_stats(list(range(2021,season+1)))),('team_stats',lambda:nfl.load_team_stats(list(range(2021,season+1)))),('schedules',lambda:nfl.load_schedules(list(range(2021,season+1)))),('teams',nfl.load_teams),('players',nfl.load_players),('rosters',lambda:nfl.load_rosters(season)),('rosters_weekly',lambda:nfl.load_rosters_weekly(season)),('snaps',lambda:nfl.load_snap_counts(list(range(2021,season+1)))),('depth_charts',lambda:nfl.load_depth_charts(season)),('trades',nfl.load_trades),('injuries',lambda:nfl.load_injuries(season)),('ftn_charting',lambda:nfl.load_ftn_charting(season)),('participation',lambda:nfl.load_participation(season-1)),('pbp',lambda:nfl.load_pbp(season))]
    specs += [('ngs_'+kind,lambda kind=kind:nfl.load_nextgen_stats(list(range(season-2,season+1)),stat_type=kind)) for kind in ['passing','rushing','receiving']]
    specs += [('pfr_'+kind,lambda kind=kind:nfl.load_pfr_advstats(season,stat_type=kind)) for kind in ['pass','rush','rec','def']]
    frames={};manifest=[]
    def load(spec):
        name,loader=spec
        try:
            frame=loader();path=lake/(name+'.parquet');frame.write_parquet(path,compression='zstd')
            return name,frame,{'dataset':name,'status':'ok','rows':frame.height,'columns':frame.columns,'retrievedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'path':name+'.parquet','source':'nflreadpy / nflverse','maxSeason':frame['season'].max() if 'season' in frame.columns else None,'maxWeek':frame.filter(pl.col('season')==season)['week'].max() if {'season','week'}.issubset(frame.columns) else None}
        except Exception as error:return name,None,{'dataset':name,'status':'unavailable','retrievedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'error':type(error).__name__,'note':'Public dataset unavailable or unsupported for the requested season; no replacement values invented.'}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for name,frame,entry in pool.map(load,specs):
            if frame is not None:frames[name]=frame
            manifest.append(entry);print(json.dumps({k:v for k,v in entry.items() if k!='columns'},default=str),flush=True)
    games=[]
    if 'schedules' in frames:
        from zoneinfo import ZoneInfo
        for game in frames['schedules'].filter(pl.col('season')==season).to_dicts():
            try:
                day=str(game['gameday'])[:10];clock=str(game.get('gametime') or '13:00')[:5];kickoff=dt.datetime.fromisoformat(day+'T'+clock).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(dt.timezone.utc)
                games.append({**game,'kickoff':kickoff.isoformat()})
            except (KeyError,ValueError):continue
    future=[g for g in games if now<dt.datetime.fromisoformat(g['kickoff'])<now+dt.timedelta(days=8)];week=min((int(g['week']) for g in future),default=1)
    bdl=collect_bdl(season,week);dump(output/'balldontlie.json',safe(bdl));weather=collect_weather(future,now);dump(output/'weather.json',safe(weather))
    # Small public subsets complement the full versioned Parquet lake.
    supplement={}
    people=frames.get('players');crosswalk={r['pfr_id']:r['gsis_id'] for r in people.select(['pfr_id','gsis_id']).to_dicts() if r.get('pfr_id') and r.get('gsis_id')} if people is not None else {}
    for name in ['ngs_passing','ngs_rushing','ngs_receiving','pfr_pass','pfr_rush','pfr_rec','pfr_def','team_stats']:
        frame=frames.get(name)
        if frame is not None:
            if 'season' in frame.columns:frame=frame.filter(pl.col('season')==season)
            records=frame.to_dicts()
            if name.startswith('pfr_'):
                for record in records:record['player_gsis_id']=crosswalk.get(record.get('pfr_player_id'))
            supplement[name]=safe(records)
    dump(output/'advanced-stats.json',{'generatedAt':now.isoformat(),'season':season,'datasets':supplement,'scope':'Current published descriptive statistics. They are not inserted retrospectively into historical model tests.'})
    games_public=safe(future);dump(output/'upcoming-games.json',{'generatedAt':now.isoformat(),'games':games_public})
    if 'pbp' in frames:
        pbp=frames['pbp'];columns=['game_id','defteam','posteam','qb_dropback','rush_attempt','epa','sack','qb_hit','yards_gained','no_play']
        pbp=pbp.select([c for c in columns if c in pbp.columns]);pbp.write_parquet(lake/'pbp_research.parquet',compression='zstd')
    # DuckDB exposes the downloaded datasets for reproducible analytical queries.
    import duckdb
    db=duckdb.connect(str(lake/'research.duckdb'))
    for path in lake.glob('*.parquet'):
        if re.fullmatch(r'[a-z_]+',path.stem):db.execute('CREATE OR REPLACE VIEW "'+path.stem+'" AS SELECT * FROM read_parquet(\''+str(path.resolve()).replace("'","''")+'\')')
    db.close()
    report={'generatedAt':now.isoformat(),'season':season,'week':week,'nflreadpy':{'status':'ok' if all(m['status']=='ok' for m in manifest) else 'partial','datasets':manifest,'authentication':'No API key required','documentation':'https://nflreadpy.nflverse.com/api/load_functions/'},'balldontlie':{k:v for k,v in bdl.items() if k!='datasets'},'balldontlieEndpoints':{k:{a:b for a,b in v.items() if a!='rows'} for k,v in bdl.get('datasets',{}).items()},'xweather':{'status':weather['xweatherStatus'],'errors':weather['errors']},'weather':{'status':'ok' if any(g['status']=='ok' for g in weather['games']) else 'unavailable','games':len(weather['games'])},'optionalProviders':{'SportsDataIO':'Not configured; licensed adapter required','PFF':'Not configured; licensed data required','Sportradar':'Not configured; licensed adapter required','NFL tracking':'No public full tracking feed configured'},'limitations':['No automatic subscriptions or purchases.','Current advanced/weather snapshots are descriptive context until their incremental value is validated with historical data.','Actual key values never appear in published snapshots.','Historical ROI and CLV require genuine pregame and closing-price archives.']}
    dump(output/'providers.json',safe(report));return report
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--season',type=int);args=parser.parse_args();run(args.season)
