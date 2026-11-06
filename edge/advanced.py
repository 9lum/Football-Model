"""Join game-level public Next Gen Stats; prepare() shifts every value before prediction."""
import os
from pathlib import Path
import pandas as pd
FIELDS={'passing':['avg_time_to_throw','avg_completed_air_yards','avg_intended_air_yards','aggressiveness','max_completed_air_distance','avg_air_yards_differential','completion_percentage_above_expectation','expected_completion_percentage'],
'receiving':['avg_cushion','avg_separation','avg_intended_air_yards','avg_yac','avg_expected_yac','avg_yac_above_expectation'],
'rushing':['efficiency','percent_attempts_gte_eight_defenders','avg_time_to_los','expected_rush_yards','rush_yards_over_expected','rush_yards_over_expected_per_att','rush_pct_over_expected']}
METRICS=['ngs_'+kind+'_'+field for kind,fields in FIELDS.items() for field in fields]
def attach(stats,start,season):
    os.environ.setdefault('NFLREADPY_CACHE','filesystem');os.environ.setdefault('NFLREADPY_CACHE_DIR',str(Path('work/nflreadpy-cache').resolve()));os.environ.setdefault('NFLREADPY_TIMEOUT','40')
    import nflreadpy as nfl
    sources=[];out=stats.copy()
    for kind,fields in FIELDS.items():
        try:
            frame=nfl.load_nextgen_stats(list(range(start,season+1)),stat_type=kind).to_pandas()
            frame=frame[frame.week.gt(0)&frame.season_type.eq('REG')];available=[c for c in fields if c in frame]
            frame=frame[['player_gsis_id','season','week',*available]].rename(columns={'player_gsis_id':'player_id',**{c:'ngs_'+kind+'_'+c for c in available}})
            if frame.duplicated(['player_id','season','week']).any():raise ValueError('Ambiguous NGS player-week rows')
            out=out.merge(frame,on=['player_id','season','week'],how='left',validate='many_to_one');sources.append({'provider':'nflreadpy Next Gen Stats','type':kind,'rows':len(frame),'status':'ok','scope':'Game-week observations, shifted before use; season aggregate week zero excluded.'})
        except Exception as error:sources.append({'provider':'nflreadpy Next Gen Stats','type':kind,'status':'unavailable','error':type(error).__name__})
    return out,sources
