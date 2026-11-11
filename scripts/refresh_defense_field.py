"""Publish the same field geometry using completions ALLOWED as its share denominator."""
import argparse,io,json
from pathlib import Path
import pandas as pd
from edge.data import get,BASE,schedule_rows
from edge.defense_field import collect
from edge.pipeline import clean

def run(reuse_cache=False):
 now=pd.Timestamp.now(tz='UTC');season=now.year if now.month>=3 else now.year-1;cache=Path('work/receiving-route-cache');cache.mkdir(parents=True,exist_ok=True);path=cache/f'play_by_play_{season}.parquet'
 if not reuse_cache or not path.exists():
  raw,_=get(BASE+'pbp/'+path.name+'?asof='+now.strftime('%Y%m%d%H'));path.write_bytes(raw)
 raw,_=get('https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv');s=schedule_rows(pd.read_csv(io.BytesIO(raw)));payload=collect(cache,season,s,now);Path('data/defense-field-profiles.json').write_text(json.dumps(clean(payload),separators=(',',':'),allow_nan=False));print(json.dumps({'season':season,'defenses':len(payload['teams']),'locatedCompletions':sum(v['season'].get('completions',0) for v in payload['teams'].values())}));return payload
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--reuse-cache',action='store_true');run(p.parse_args().reuse_cache)
