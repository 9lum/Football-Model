"""Small per-player historical stat files for honest season and last-N-game research."""
import json
import math
import os
import re
from pathlib import Path
import pandas as pd
from edge.data import normalize_stats,add_snap_zeros,schedule_rows
from edge.profiles import COUNTERS
ROOT=Path(__file__).resolve().parents[1]
NGS_FIELDS={'passing':['attempts','completions','avg_time_to_throw','completion_percentage_above_expectation'],'rushing':['rush_attempts','rush_yards_over_expected','rush_yards_over_expected_per_att'],'receiving':['targets','receptions','avg_separation','avg_yac_above_expectation']}
PFR_FIELDS={'pass':['times_pressured','times_blitzed','times_hurried','times_hit','passing_bad_throws','passing_drops'],'rush':['carries','rushing_yards_before_contact','rushing_yards_after_contact','rushing_broken_tackles'],'rec':['receiving_drop','passing_drops','receiving_broken_tackles']}
def safe(value):
    if value is None:return None
    if isinstance(value,(float,int)):
        return float(value) if math.isfinite(value) else None
    try:
        if pd.isna(value):return None
    except (TypeError,ValueError):pass
    return value.item() if hasattr(value,'item') else value

def run():
    os.environ.setdefault('NFLREADPY_CACHE','filesystem');os.environ.setdefault('NFLREADPY_CACHE_DIR',str(ROOT/'work/nflreadpy-cache'))
    import nflreadpy as nfl
    now=pd.Timestamp.now(tz='UTC');season=now.year if now.month>=3 else now.year-1;years=list(range(2021,season+1));directory=ROOT/'data/player-research';directory.mkdir(parents=True,exist_ok=True)
    bundle=json.loads((ROOT/'data/latest.json').read_text());ids={p['playerId'] for p in [*bundle.get('players',[]),*bundle.get('forecasts',[])]}
    try:
        depth=json.loads((ROOT/'data/availability.json').read_text());ids.update(p['playerId'] for p in depth.get('roster',[]))
    except (OSError,ValueError):pass
    ids={pid for pid in ids if re.fullmatch(r'[A-Za-z0-9_-]{1,80}',pid)}
    stats=normalize_stats(nfl.load_player_stats(years).to_pandas(),positions=['QB','RB','WR','TE']);people=nfl.load_players().to_pandas();snaps=nfl.load_snap_counts(years).to_pandas();stats,_=add_snap_zeros(stats,snaps,people);schedule=schedule_rows(nfl.load_schedules(years).to_pandas())
    frame=stats.drop(columns=['game_id','opponent_team'],errors='ignore').merge(schedule,on=['season','week','team'],validate='many_to_one');frame=frame[frame.player_id.isin(ids)&frame.completed&(frame.kickoff<now)].sort_values('kickoff');crosswalk_rows=people[['pfr_id','gsis_id']].dropna().drop_duplicates();crosswalk_rows=crosswalk_rows[~crosswalk_rows.pfr_id.duplicated(keep=False)];crosswalk=dict(zip(crosswalk_rows.pfr_id,crosswalk_rows.gsis_id));maps={};sources=[]
    for category,fields in NGS_FIELDS.items():
        name='ngs_'+category
        try:
            data=nfl.load_nextgen_stats(years,stat_type=category).to_pandas();data=data[data.week.gt(0)&data.season_type.eq('REG')];mapping={}
            for r in data.to_dict('records'):
                pid=r.get('player_gsis_id')
                if pid in ids:mapping[(pid,int(r['season']),int(r['week']))]={k:safe(r.get(k)) for k in fields}
            maps[name]=mapping;sources.append({'dataset':name,'status':'ok','matchedGames':len(mapping)})
        except Exception as error:maps[name]={};sources.append({'dataset':name,'status':'unavailable','error':type(error).__name__})
    for category,fields in PFR_FIELDS.items():
        name='pfr_'+category
        try:
            data=nfl.load_pfr_advstats(years,stat_type=category).to_pandas()
            if 'game_type' in data:data=data[data.game_type.eq('REG')]
            mapping={}
            for r in data.to_dict('records'):
                pid=crosswalk.get(r.get('pfr_player_id'))
                if pid in ids:mapping[(pid,int(r['season']),int(r['week']))]={k:safe(r.get(k)) for k in fields}
            maps[name]=mapping;sources.append({'dataset':name,'status':'ok','matchedGames':len(mapping)})
        except Exception as error:maps[name]={};sources.append({'dataset':name,'status':'unavailable','error':type(error).__name__})
    profiles={};count=0
    for pid,games in frame.groupby('player_id',sort=False):
        rows=[]
        for r in games.to_dict('records'):
            key=(pid,int(r['season']),int(r['week']));rows.append({'season':int(r['season']),'week':int(r['week']),'gameId':r['game_id'],'kickoff':r['kickoff'].isoformat(),'team':r['team'],'opponent':r['opponent_team'],'basic':{k:safe(r.get(k)) for k in COUNTERS},'snap':{k:safe(r.get(k)) for k in ['offense_snaps','offense_pct']},'advanced':{source:values[key] for source,values in maps.items() if key in values}})
        profiles[pid]=rows;count+=len(rows)
    for pid in ids:
        games=profiles.get(pid,[]);payload={'schemaVersion':1,'playerId':pid,'generatedAt':now.isoformat(),'seasons':sorted({g['season'] for g in games},reverse=True),'games':games,'sources':sources,'scope':'Regular-season recorded player/snap games only; DNPs are not zero-filled. Current advanced snapshots are descriptive and do not alter archived forecasts.'};(directory/(pid+'.json')).write_text(json.dumps(payload,separators=(',',':'),allow_nan=False))
    (ROOT/'data/player-research-index.json').write_text(json.dumps({'generatedAt':now.isoformat(),'players':len(ids),'gameRecords':count,'startSeason':2021,'latestSeason':season,'sources':sources},separators=(',',':')));print(json.dumps({'players':len(ids),'gameRecords':count,'sources':sources},indent=2))
if __name__=='__main__':run()
