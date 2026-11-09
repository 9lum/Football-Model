"""Point-in-time target-depth/location proxies. These are not charted route-run concepts."""
from pathlib import Path
import numpy as np
import pandas as pd
from .data import team
DEPTHS=['short','intermediate','deep'];AREAS=['left','middle','right']
COLUMNS=['game_id','play_id','season','season_type','posteam','defteam','receiver_player_id','air_yards','pass_location','complete_pass','yards_gained','epa','pass_attempt','no_play','defense_man_zone_type']
def target_records(pbp,participation=None):
 d=pbp.copy()
 if participation is not None and not participation.empty:
  p=participation.rename(columns={'nflverse_game_id':'game_id'})
  if 'defense_man_zone_type' in p:
   d=d.drop(columns=['defense_man_zone_type'],errors='ignore').merge(p[['game_id','play_id','defense_man_zone_type']].drop_duplicates(['game_id','play_id']),on=['game_id','play_id'],how='left',validate='many_to_one')
 for c in COLUMNS:
  if c not in d:d[c]=np.nan
 d=d[d.receiver_player_id.notna()&d.pass_attempt.eq(1)&~d.no_play.eq(1)&d.season_type.eq('REG')].copy()
 d['air_yards']=pd.to_numeric(d.air_yards,errors='coerce');d=d[d.air_yards.notna()&d.pass_location.isin(AREAS)]
 d['depth']=np.where(d.air_yards<10,'short',np.where(d.air_yards<20,'intermediate','deep'));d['region']=d.depth+'_'+d.pass_location
 d['coverage']=d.defense_man_zone_type.fillna('').str.upper().map({'MAN':'man','MAN_COVERAGE':'man','ZONE':'zone','ZONE_COVERAGE':'zone'})
 d['team']=d.posteam.map(team);d['opponent']=d.defteam.map(team)
 for c in ['complete_pass','yards_gained','epa']:d[c]=pd.to_numeric(d[c],errors='coerce')
 return d

def load_targets(season,cache,schedules):
 import pyarrow.parquet as pq
 frames=[];sources=[]
 for year in [season-1,season]:
  path=Path(cache)/f'play_by_play_{year}.parquet'
  if not path.exists():continue
  available=pq.read_schema(path).names;d=pd.read_parquet(path,columns=[c for c in COLUMNS if c in available]);part_path=Path(cache)/f'pbp_participation_{year}.parquet';part=None
  if part_path.exists():
   columns=pq.read_schema(part_path).names
   part=pd.read_parquet(part_path,columns=[c for c in ['nflverse_game_id','game_id','play_id','defense_man_zone_type'] if c in columns])
  d=target_records(d,part);frames.append(d);sources.append({'season':year,'source':f'https://github.com/nflverse/nflverse-data/releases/tag/pbp','targets':len(d),'coverageSource':'nflverse participation charting' if part is not None else 'PBP when labeled'})
 if not frames:return pd.DataFrame(),sources
 d=pd.concat(frames,ignore_index=True)
 completed=schedules[schedules.completed][['game_id','kickoff']].drop_duplicates('game_id')
 return d.merge(completed,on='game_id',how='inner',validate='many_to_one').sort_values('kickoff'),sources

def number(x):return float(x) if pd.notna(x) and np.isfinite(x) else None
def summarize(g,scope):
 if g.empty:return {'status':'unavailable','reason':'No published targeted-pass depth/location sample','scope':scope,'routeTypes':[]}
 n=len(g);recs=number(g.complete_pass.sum(min_count=1));yards=number(g.yards_gained.sum(min_count=1));zones=[]
 for depth in DEPTHS:
  for area in AREAS:
   selected=g[(g.depth==depth)&(g.pass_location==area)];count=len(selected)
   zones.append({'depth':depth,'area':area,'targets':count,'targetShare':count/n,'catchRate':number(selected.complete_pass.mean()),'yardsPerTarget':number(selected.yards_gained.mean()),'epaPerTarget':number(selected.epa.mean()),'airYards':number(selected.air_yards.mean())})
 return {'status':'available','scope':scope,'season':int(g.season.max()),'games':g.game_id.nunique(),'targets':n,'receptions':recs,'receivingYards':yards,'adot':number(g.air_yards.mean()),'catchRate':number(g.complete_pass.mean()),'yardsPerTarget':number(g.yards_gained.mean()),'depthShares':{depth:float(g.depth.eq(depth).mean()) for depth in DEPTHS},'zones':zones,'routeTypes':[],'asOf':g.kickoff.max().isoformat(),'definition':'Share of recorded targets with known air yards and left/middle/right location; not share of all routes run. Short <10 air yards, intermediate 10–19, deep ≥20. Actual route concepts are not publicly charted here.','source':'https://github.com/nflverse/nflverse-data/releases/tag/pbp'}

class RouteContext:
 def __init__(self,records,season):
  self.records=records;self.season=season;self.players={pid:g for pid,g in records.groupby('receiver_player_id')} if not records.empty else {};self.defenses={club:g for club,g in records.groupby('opponent')} if not records.empty else {};self.def_cache={}
  prior=records[records.season.lt(season)] if not records.empty else pd.DataFrame();self.league={r:g for r,g in prior.groupby('region')} if not prior.empty else {}
 def history(self,pid,cutoff,games=6):
  g=self.players.get(pid)
  if g is None:return pd.DataFrame()
  g=g[g.kickoff<cutoff]
  if games:g=g[g.game_id.isin(g[['game_id','kickoff']].drop_duplicates().sort_values('kickoff').tail(games).game_id)]
  return g
 def profile(self,pid,cutoff):
  season=self.history(pid,cutoff,None);season=season[season.season.eq(self.season)] if not season.empty else season
  return {'season':summarize(season,'Current season'),**{f'last{n}':summarize(self.history(pid,cutoff,n),f'Last {n} recorded games') for n in [3,6,9]}}
 def context(self,row):
  cutoff=row.kickoff;h=self.history(row.player_id,cutoff,6)
  if not h.empty and getattr(row,'team',None):h=h[h.team.eq(row.team)]
  profile=summarize(h,'Last six recorded games');base={'profile':profile,'basis':'Target depth/location proxy, not actual routes run','routeTypesAvailable':False}
  if h.empty or len(h)<20 or h.game_id.nunique()<3 or not self.league or cutoff-h.kickoff.max()>pd.Timedelta(days=35):return {**base,'status':'unavailable','reason':'Requires 20 current-team targeted passes, three prior games, a prior-season league reference and a sample within 35 days','signal':0.}
  key=(row.opponent_team,cutoff)
  if key not in self.def_cache:
   defense=self.defenses.get(row.opponent_team,pd.DataFrame())
   if not defense.empty:
    defense=defense[defense.kickoff<cutoff];ids=defense[['game_id','kickoff']].drop_duplicates().sort_values('kickoff').tail(6).game_id;defense=defense[defense.game_id.isin(ids)]
   self.def_cache[key]=defense
  defense=self.def_cache[key]
  if defense.empty or len(defense)<100 or cutoff-defense.kickoff.max()>pd.Timedelta(days=35):return {**base,'status':'unavailable','reason':'Opponent needs 100 prior targeted passes with depth/location and a sample within 35 days','signal':0.}
  evidence=[];signal=0.
  for region,p in h.groupby('region'):
   league=self.league.get(region);allowed=defense[defense.region.eq(region)]
   if league is None or len(league)<50:continue
   ly=league.yards_gained.mean();le=league.epa.mean()
   if not np.isfinite(ly) or not np.isfinite(le):continue
   n=len(allowed);dy=(allowed.yards_gained.dropna().sum()+30*ly)/(allowed.yards_gained.notna().sum()+30);de=(allowed.epa.dropna().sum()+30*le)/(allowed.epa.notna().sum()+30);py=(p.yards_gained.dropna().sum()+20*ly)/(p.yards_gained.notna().sum()+20)
   weakness=np.clip((dy-ly)/max(abs(ly),1)+.2*(de-le),-.5,.5);strength=np.clip((py-ly)/max(abs(ly),1),-.3,.5);share=len(p)/len(h)
   signal+=share*weakness*(1+strength)
   evidence.append({'region':region,'playerTargetShare':share,'playerTargets':len(p),'playerYardsPerTarget':py,'defenseTargets':n,'defenseYardsPerTarget':dy,'defenseEPA':de,'leagueYardsPerTarget':float(ly),'leagueEPA':float(le)})
  man=number(getattr(row,'matchup_man_rate',np.nan));zone=number(getattr(row,'matchup_zone_rate',np.nan));labeled=self.history(row.player_id,cutoff,None)
  labeled=labeled[labeled.coverage.notna()] if not labeled.empty else labeled
  efficiency={c:{'targets':int(labeled.coverage.eq(c).sum()),'yardsPerTarget':number(labeled[labeled.coverage.eq(c)].yards_gained.mean()),'catchRate':number(labeled[labeled.coverage.eq(c)].complete_pass.mean())} for c in ['man','zone']} if not labeled.empty else {}
  confidence=min(1,len(h)/50,len(defense)/200);signal=float(np.clip(signal*confidence,-.5,.5))
  return {**base,'status':'available','signal':signal,'direction':1 if signal>=.03 else -1 if signal<=-.03 else 0,'evidence':evidence,'manRate':man,'zoneRate':zone,'coverageEfficiency':efficiency,'coverageEfficiencyScope':'Historical labeled targets strictly before kickoff; potentially prior-season charting','defensiveGames':defense.game_id.nunique(),'coverageDoubleCountProtection':'No second man/zone multiplier: scheme tendencies and receiver scheme efficiency already enter the core feature assessment.'}

def attach_route_context(frame,season,cache,schedules,now):
 records,sources=load_targets(season,cache,schedules);engine=RouteContext(records,season);d=frame.copy();d['routeContext']=[engine.context(r) if r.season==season and r.position in ['WR','TE','RB'] else {'status':'not_applicable','signal':0.} for r in d.itertuples()]
 return d,engine,sources
