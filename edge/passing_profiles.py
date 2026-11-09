"""Observed QB throwing locations and rushing decisions, never inferred routes."""
from pathlib import Path
import pandas as pd
from .receiving_routes import summarize,DEPTHS,AREAS,number
COLUMNS=['game_id','play_id','season','season_type','passer_player_id','rusher_player_id','pass_attempt','rush_attempt','qb_dropback','qb_scramble','qb_kneel','qb_spike','sack','no_play','air_yards','pass_location','complete_pass','yards_gained','epa','cpoe']

def quarterback_records(pbp,schedules,now):
 d=pbp.copy()
 for c in COLUMNS:
  if c not in d:d[c]=float('nan')
 d=d[d.season_type.eq('REG')&~d.no_play.eq(1)&~d.qb_kneel.eq(1)&~d.qb_spike.eq(1)].copy()
 d['isScramble']=d.qb_scramble.eq(1)
 d['isThrow']=d.pass_attempt.eq(1)&~d.sack.eq(1)&~d.isScramble
 d['isDesignedRun']=d.rush_attempt.eq(1)&~d.isScramble
 d['isDropback']=d.qb_dropback.eq(1)|d.isThrow|d.isScramble|d.sack.eq(1)
 # Rusher identity determines run credit; passer identity determines throwing credit.
 d['playerId']=d.passer_player_id.where(d.isDropback&~d.isScramble,d.rusher_player_id)
 d['playerId']=d.playerId.where(d.playerId.notna(),d.passer_player_id.where(d.isScramble))
 d=d[d.playerId.notna()&(d.isDropback|d.isDesignedRun)]
 done=schedules[schedules.completed&(schedules.kickoff<now)][['game_id','kickoff']].drop_duplicates('game_id')
 return d.merge(done,on='game_id',how='inner',validate='many_to_one').sort_values('kickoff')

def passing_summary(g,scope):
 if g.empty:return {'status':'unavailable','kind':'passing','scope':scope,'reason':'No completed public QB play-by-play in this sample'}
 located=g[g.isThrow&g.air_yards.notna()&g.pass_location.isin(AREAS)].copy()
 located['depth']=pd.cut(located.air_yards,[-float('inf'),10,20,float('inf')],right=False,labels=DEPTHS).astype(str)
 # Reuse the same nine-zone schema for interactive receiver and QB fields.
 profile=summarize(located,scope);throws=g[g.isThrow];dropbacks=int(g.isDropback.sum());scrambles=g[g.isScramble];designed=g[g.isDesignedRun]
 known_rush=g.rush_attempt.eq(1);rush_labels_known=bool(g.loc[known_rush,'qb_scramble'].notna().all())
 # Missing scramble labels cannot safely be interpreted as designed-run zeros.
 profile.update({'kind':'passing','status':'available' if not located.empty else 'unavailable','scope':scope,'games':int(g.game_id.nunique()),'throwAttempts':len(throws),'locatedAttempts':len(located),'completionRate':number(throws.complete_pass.mean()),'yardsPerAttempt':number(throws.yards_gained.mean()),'epaPerDropback':number(g.loc[g.isDropback,'epa'].mean()),'cpoe':number(throws.cpoe.mean()),'dropbacks':dropbacks,'scrambles':len(scrambles) if rush_labels_known else None,'scrambleRate':len(scrambles)/dropbacks if dropbacks and rush_labels_known else None,'scrambleYards':(0 if scrambles.empty else number(scrambles.yards_gained.sum(min_count=1))) if rush_labels_known else None,'designedRushAttempts':len(designed) if rush_labels_known else None,'designedRushShare':len(designed)/(len(designed)+len(scrambles)) if len(designed)+len(scrambles) and rush_labels_known else None,'designedRushYards':(0 if designed.empty else number(designed.yards_gained.sum(min_count=1))) if rush_labels_known else None,'asOf':g.kickoff.max().isoformat(),'definition':'Field percentages use thrown passes with known air yards and left/middle/right location. Scramble rate uses dropbacks including sacks. Designed carries are non-scramble QB runs; kneels, spikes and no-plays excluded. Play-by-play classifications are not playbook intent or tracking.','source':'https://github.com/nflverse/nflverse-data/releases/tag/pbp'})
 return profile

def quarterback_profiles(season,cache,schedules,now,player_ids):
 import pyarrow.parquet as pq
 path=Path(cache)/f'play_by_play_{season}.parquet'
 if not path.exists():return {}
 columns=pq.read_schema(path).names
 d=pd.read_parquet(path,columns=[c for c in COLUMNS if c in columns]);records=quarterback_records(d,schedules,now);groups=dict(tuple(records.groupby('playerId')));profiles={}
 for pid in player_ids:
  g=groups.get(pid,pd.DataFrame());periods={'season':passing_summary(g,'Current season')}
  for n in [3,6,9]:
   recent=g[g.game_id.isin(g[['game_id','kickoff']].drop_duplicates().tail(n).game_id)] if not g.empty else g
   periods[f'last{n}']=passing_summary(recent,f'Last {n} games with QB plays')
  profiles[pid]=periods
 return profiles
