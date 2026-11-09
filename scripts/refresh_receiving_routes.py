"""Publish actual target-depth profiles independently of slower model fitting."""
import datetime as dt
import json
from pathlib import Path
from scripts.model_record import read
from edge.data import schedule_rows
from edge.context import parquet_asset,PART_COLUMNS
from edge.receiving_routes import COLUMNS,load_targets,RouteContext

def collect(output=Path('data'),now=None):
 import nflreadpy as nfl
 import pandas as pd
 now=pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now);season=now.year if now.month>=3 else now.year-1;cache=Path('work/receiving-route-cache');warnings=[]
 for year in [season-1,season]:
  try:
   if year==season:
    from edge.data import get,BASE
    raw,_=get(BASE+'pbp/'+f'play_by_play_{year}.parquet?asof='+now.strftime('%Y%m%d%H'));cache.mkdir(exist_ok=True,parents=True);(cache/f'play_by_play_{year}.parquet').write_bytes(raw)
   else:parquet_asset('pbp',f'play_by_play_{year}.parquet',COLUMNS,cache,immutable=True)
  except Exception as error:
   warnings.append({'season':year,'error':type(error).__name__,'cachedFallback':(cache/f'play_by_play_{year}.parquet').exists()})
   fallback=Path('work/defense-cache')/f'play_by_play_{year}.parquet'
   if not (cache/f'play_by_play_{year}.parquet').exists() and fallback.exists():
    import shutil
    shutil.copy2(fallback,cache/fallback.name)
  if year<season:
   try:parquet_asset('pbp_participation',f'pbp_participation_{year}.parquet',PART_COLUMNS,cache,immutable=True)
   except Exception:pass
 from edge.data import get
 import io
 try:
  raw,_=get('https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv');schedule=pd.read_csv(io.BytesIO(raw));schedule=schedule[schedule.season.isin([season-1,season])]
 except Exception:schedule=nfl.load_schedules([season-1,season]).to_pandas()
 schedules=schedule_rows(schedule);records,sources=load_targets(season,cache,schedules);records=records[records.kickoff<now] if not records.empty else records;engine=RouteContext(records,season)
 latest=read(Path(output)/'latest.json');players={p['playerId']:engine.profile(p['playerId'],now) for p in latest.get('players',[]) if p['position'] in ['WR','TE','RB']}
 payload={'generatedAt':now.isoformat(),'season':season,'players':players,'sources':sources,'sourceWarnings':warnings,'scope':'Published targeted-pass air depth/location shares, not percentages of route concepts or all routes run.'}
 from edge.pipeline import clean
 Path(output).mkdir(exist_ok=True,parents=True);Path(output,'receiving-route-profiles.json').write_text(json.dumps(clean(payload),separators=(',',':'),allow_nan=False));print(json.dumps({'players':len(players),'targets':len(records),'season':season}));return payload
if __name__=='__main__':collect()
