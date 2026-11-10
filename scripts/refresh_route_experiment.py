"""Experimental charted TARGET-route trees; never percentages of all routes run."""
import json
from pathlib import Path
import pandas as pd
from edge.context import parquet_asset
SOURCE='https://github.com/nflverse/nflverse-data/releases/tag/pbp_participation'
GROUPS={'GO':'go','POST':'post','IN/DIG':'dig','HITCH/CURL':'curl','SLANT':'slant','SCREEN':'screen','QUICK OUT':'out','DEEP OUT':'out','SHALLOW CROSS/DRAG':'cross','CORNER':'corner','SWING':'other','WHEEL':'other','TEXAS/ANGLE':'other'}
COLS=['game_id','play_id','season','season_type','week','game_date','posteam','receiver_player_id','passer_player_id','pass_attempt','play_type','no_play','complete_pass','yards_gained','air_yards','epa']
def summarize(g):
 known=g[g.route.isin(GROUPS)].copy();n=len(known)
 if not n:return None
 known['concept']=known.route.map(GROUPS);routes=[]
 for key in dict.fromkeys(GROUPS.values()):
  r=known[known.concept.eq(key)];num=lambda c:float(r[c].mean()) if len(r) and r[c].notna().any() else None
  routes.append({'key':key,'targets':len(r),'share':len(r)/n,'catchRate':num('complete_pass'),'yardsPerTarget':num('yards_gained'),'airYards':num('air_yards'),'epaPerTarget':num('epa'),'components':r.route.value_counts().to_dict()})
 return {'status':'available','chartedTargets':n,'totalTargets':len(g),'coverage':n/len(g),'games':g.game_id.nunique(),'lastWeek':int(g.week.max()),'asOf':str(g.game_date.max()),'routes':routes,'source':SOURCE,'denominator':'Charted targeted passes, not all routes run'}
def aggregate(pbp,part):
 p=part.rename(columns={'nflverse_game_id':'game_id'})[['game_id','play_id','route']].drop_duplicates()
 if p.duplicated(['game_id','play_id']).any():raise ValueError('Conflicting route labels for a play')
 if 'no_play' not in pbp:pbp=pbp.assign(no_play=pbp.play_type.eq('no_play'))
 d=pbp[(pbp.season_type=='REG')&pbp.pass_attempt.eq(1)&~pbp.no_play.eq(1)&pbp.receiver_player_id.notna()].merge(p,on=['game_id','play_id'],how='left',validate='one_to_one')
 output={}
 for kind,col in [('receiving','receiver_player_id'),('passing','passer_player_id')]:
  for pid,g in d[d[col].notna()].groupby(col):
   item={'kind':kind,'season':summarize(g)}
   for n in [3,6,9]:
    ids=g[['game_id','week']].drop_duplicates().sort_values('week').tail(n).game_id;item['last'+str(n)]=summarize(g[g.game_id.isin(ids)])
   if item['season']:
    if pid in output:output[pid]['passingProfile']=item
    else:output[pid]=item
 return output

def run():
 now=pd.Timestamp.now(tz='UTC');year=now.year if now.month>=3 else now.year-1;cache=Path('work/receiving-route-cache');players={};sources=[]
 import pyarrow.parquet as pq
 for season in [year-1,year]:
  try:
   path=cache/f'pbp_participation_{season}.parquet'
   if season==year or not path.exists():parquet_asset('pbp_participation',path.name,['nflverse_game_id','game_id','play_id','route'],cache,immutable=season<year)
   part=pd.read_parquet(path,columns=[c for c in ['nflverse_game_id','game_id','play_id','route'] if c in pq.read_schema(path).names])
   if 'route' not in part or not part.route.fillna('').isin(GROUPS).any():raise ValueError('No charted route concepts published')
   path=cache/f'play_by_play_{season}.parquet'
   if not path.exists():parquet_asset('pbp',path.name,COLS,cache,immutable=season<year)
   pbp=pd.read_parquet(path,columns=[c for c in COLS if c in pq.read_schema(path).names]);values=aggregate(pbp,part)
   for pid,v in values.items():players.setdefault(pid,{})[str(season)]=v
   sources.append({'season':season,'status':'available','players':len(values),'source':SOURCE})
  except Exception as e:sources.append({'season':season,'status':'unavailable','reason':str(e)[:180],'source':SOURCE})
 if not players:raise RuntimeError('No verified charted routes available; keeping the previously published experiment')
 payload={'generatedAt':now.isoformat(),'currentSeason':year,'players':players,'sources':sources,'license':'FTN Data via nflverse, CC BY-SA 4.0. Aggregated and grouped for this experimental display.','definition':'Shares of charted targeted passes only. Out combines QUICK OUT + DEEP OUT; Other combines SWING + WHEEL + TEXAS/ANGLE. No comeback classification is supplied. Historical seasons are not current roles.'}
 from edge.pipeline import clean
 Path('data/route-experiment.json').write_text(json.dumps(clean(payload),separators=(',',':'),allow_nan=False));print(json.dumps({'players':len(players),'sources':sources}))
if __name__=='__main__':run()
