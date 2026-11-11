"""Located completions allowed by defense; shares describe completions, not target volume."""
from pathlib import Path
import numpy as np
import pandas as pd
from .data import team
DEPTHS=['behind','short','intermediate','deep'];AREAS=['left','middle','right']
SOURCE='https://github.com/nflverse/nflverse-data/releases/tag/pbp'
def number(v):return float(v) if pd.notna(v) and np.isfinite(v) else None

def summarize(rows,games=None):
 passes=rows[rows.pass_attempt.eq(1)&~rows.no_play.eq(1)].copy()
 for key in ['two_point_attempt','qb_spike']:
  if key in passes:passes=passes[~passes[key].eq(1)]
 known=passes[passes.complete_pass.isin([0,1])].copy();located=known[known.air_yards.notna()&known.pass_location.isin(AREAS)].copy();located['depth']=np.where(located.air_yards.lt(0),'behind',np.where(located.air_yards.lt(10),'short',np.where(located.air_yards.lt(20),'intermediate','deep')))
 n=len(located);caught=located[located.complete_pass.eq(1)];completions=len(caught);all_completions=int(known.complete_pass.eq(1).sum());zones=[]
 if not n:return {'status':'unavailable','reason':'No completed-game passes with known outcomes, air depth and field side.','games':games if games is not None else rows.game_id.nunique(),'totalCompletions':all_completions,'source':SOURCE}
 for depth in DEPTHS:
  for area in AREAS:
   g=located[located.depth.eq(depth)&located.pass_location.eq(area)];c=g[g.complete_pass.eq(1)]
   zones.append({'depth':depth,'area':area,'targets':len(g),'completions':len(c),'completionShare':len(c)/completions if completions else None,'targetShare':len(g)/n,'catchRate':len(c)/len(g) if len(g) else None,'yardsPerTarget':number(g.yards_gained.mean()),'yardsPerCompletion':number(c.yards_gained.mean()),'epaPerTarget':number(g.epa.mean()),'epaSamples':int(g.epa.notna().sum()),'airYards':number(g.air_yards.mean())})
 behind=caught[caught.depth.eq('behind')]
 return {'status':'available','season':int(located.season.max()),'games':int(games if games is not None else rows.game_id.nunique()),'targets':n,'completions':completions,'totalCompletions':all_completions,'unlocatedCompletions':all_completions-completions,'unknownOutcomePasses':int((~passes.complete_pass.isin([0,1])).sum()),'completionLocationCoverage':completions/all_completions if all_completions else None,'passingYards':number(caught.yards_gained.sum(min_count=1)) if completions else 0,'catchRate':completions/n,'yardsPerCompletion':number(caught.yards_gained.mean()),'adot':number(located.air_yards.mean()),'behindLineCompletions':len(behind),'behindLineCompletionShare':len(behind)/completions if completions else None,'behindLineYards':number(behind.yards_gained.sum(min_count=1)) if len(behind) else 0,'depthShares':{depth:len(caught[caught.depth.eq(depth)])/completions if completions else None for depth in DEPTHS},'zones':zones,'asOf':rows.kickoff.max().isoformat() if 'kickoff' in rows and len(rows) else None,'source':SOURCE,'definition':'Spikes, two-point attempts and nullified plays are excluded. Zone percentages are shares of located completions allowed. Air depth is measured at the target, not after the catch. Left/middle/right use the offense’s perspective. Unknown locations or outcomes are excluded, not assigned to a zone.'}

def build(pbp,schedules,season,now):
 d=pbp[pbp.season.eq(season)&pbp.season_type.eq('REG')].copy()
 if 'no_play' not in d:d['no_play']=d.play_type.eq('no_play') if 'play_type' in d else np.nan
 if d.duplicated(['game_id','play_id']).any():raise ValueError('Duplicate play identities')
 completed=schedules[schedules.completed&schedules.kickoff.lt(now)][['game_id','kickoff']].drop_duplicates('game_id');d=d.merge(completed,on='game_id',how='inner',validate='many_to_one');d=d[d.defteam.notna()&d.defteam.astype(str).ne('')].copy();d['defense']=d.defteam.map(team)
 for key in ['air_yards','complete_pass','yards_gained','epa']:d[key]=pd.to_numeric(d[key],errors='coerce')
 output={}
 for club,g in d[d.defense.notna()].groupby('defense'):
  ids=g[['game_id','kickoff']].drop_duplicates().sort_values('kickoff').game_id.tolist();output[club]={'season':summarize(g,len(ids))}
  for n in [3,6,9]:output[club]['last'+str(n)]=summarize(g[g.game_id.isin(ids[-n:])],min(n,len(ids)))
 return output

def collect(cache,season,schedules,now):
 import pyarrow.parquet as pq
 path=Path(cache)/f'play_by_play_{season}.parquet';cols=['game_id','play_id','season','season_type','defteam','pass_attempt','no_play','play_type','two_point_attempt','qb_spike','complete_pass','air_yards','pass_location','yards_gained','epa'];names=pq.read_schema(path).names;pbp=pd.read_parquet(path,columns=[c for c in cols if c in names]);teams=build(pbp,schedules,season,now)
 if len(teams)!=32:raise ValueError('Incomplete defense-team play-by-play coverage')
 return {'schemaVersion':1,'generatedAt':now.isoformat(),'season':season,'teams':teams,'scope':'Current regular season; confirmed completed games only. Completions allowed by located target depth and side. Not tracking-derived coverage responsibility.','source':SOURCE}
