"""Transparent current-season position-group production indices from public weekly stats."""
import io,json
from pathlib import Path
import numpy as np
import pandas as pd
from edge.data import get,BASE,team
TEAMS='ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LAC LAR LV MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS'.split()
GROUPS={'QB':['QB'],'RB':['RB','HB','FB'],'WR':['WR'],'TE':['TE'],'DL':['DE','DT','NT','DL','EDGE','ED','OLB'],'LB':['LB','MLB','ILB'],'CB':['CB'],'S':['S','SAF','FS','SS']}
LABELS={'QB':'Quarterbacks','RB':'Running backs','WR':'Wide receivers','TE':'Tight ends','OL':'Offensive line','DL':'Defensive line / edge','LB':'Linebackers','CB':'Cornerbacks','S':'Safeties'}
WEIGHTS={'QB':{'epaPerPlay':.65,'yardsPerPlay':.25,'turnoversPerPlay':-.1},'RB':{'epaPerOpportunity':.45,'yardsPerGame':.4,'touchdownsPerGame':.15},'WR':{'epaPerTarget':.5,'yardsPerGame':.35,'touchdownsPerGame':.15},'TE':{'epaPerTarget':.5,'yardsPerGame':.35,'touchdownsPerGame':.15},'OL':{'sackRate':-.65,'rbRushEpaPerCarry':.35},'DL':{'sacksPerGame':.6,'tflPerGame':.25,'hitsPerGame':.15},'LB':{'tflPerGame':.35,'passesDefendedPerGame':.25,'soloTacklesPerGame':.25,'forcedFumblesPerGame':.15},'CB':{'passesDefendedPerGame':.6,'interceptionsPerGame':.3,'forcedFumblesPerGame':.1},'S':{'interceptionsPerGame':.45,'passesDefendedPerGame':.35,'forcedFumblesPerGame':.2}}
def build(stats,season):
 d=stats[(stats.season==season)&(stats.season_type=='REG')&stats.week.gt(0)].copy();d['team']=d.team.map(team)
 if d.duplicated(['player_id','game_id','team']).any():raise ValueError('Duplicate player-game statistics')
 result=[]
 for club in TEAMS:
  own=d[d.team==club];gp=own.game_id.nunique();units={}
  for group,positions in GROUPS.items():
   g=own[own.position.isin(positions)]
   def total(key):
    v=pd.to_numeric(g[key],errors='coerce');return float(v.sum(min_count=1)) if v.notna().any() else None
   def add(*keys):
    values=[total(k) for k in keys];return sum(values) if all(v is not None for v in values) else None
   def rate(value,den):return value/den if value is not None and den is not None and den>0 else None
   if group=='QB':
    plays=add('attempts','sacks_suffered','carries');metrics={'epaPerPlay':rate(add('passing_epa','rushing_epa'),plays),'yardsPerPlay':rate(add('passing_yards','rushing_yards','sack_yards_lost'),plays),'turnoversPerPlay':rate(add('passing_interceptions','sack_fumbles_lost','rushing_fumbles_lost'),plays)}
   elif group=='RB':metrics={'epaPerOpportunity':rate(add('rushing_epa','receiving_epa'),add('carries','targets')),'yardsPerGame':rate(add('rushing_yards','receiving_yards'),gp),'touchdownsPerGame':rate(add('rushing_tds','receiving_tds'),gp)}
   elif group in ['WR','TE']:metrics={'epaPerTarget':rate(total('receiving_epa'),total('targets')),'yardsPerGame':rate(total('receiving_yards'),gp),'touchdownsPerGame':rate(total('receiving_tds'),gp)}
   else:
    fields={'sacksPerGame':'def_sacks','tflPerGame':'def_tackles_for_loss','hitsPerGame':'def_qb_hits','passesDefendedPerGame':'def_pass_defended','soloTacklesPerGame':'def_tackles_solo','forcedFumblesPerGame':'def_fumbles_forced','interceptionsPerGame':'def_interceptions'};metrics={key:rate(total(fields[key]),gp) for key in WEIGHTS[group]}
   units[group]={'metrics':metrics,'players':int(g.player_id.nunique()),'rank':None,'score':None}
  qb=units['QB'];backs=own[own.position.isin(GROUPS['RB'])];sacks=pd.to_numeric(own.sacks_suffered,errors='coerce').sum(min_count=1);attempts=pd.to_numeric(own.attempts,errors='coerce').sum(min_count=1);carries=pd.to_numeric(backs.carries,errors='coerce').sum(min_count=1);epa=pd.to_numeric(backs.rushing_epa,errors='coerce').sum(min_count=1)
  units['OL']={'metrics':{'sackRate':float(sacks/(attempts+sacks)) if attempts+sacks>0 else None,'rbRushEpaPerCarry':float(epa/carries) if carries>0 else None},'rank':None,'score':None,'proxy':True}
  result.append({'team':club,'games':int(gp),'throughWeek':int(own.week.max()) if gp else None,'units':units})
 for group,weights in WEIGHTS.items():
  valid=[r for r in result if all(r['units'][group]['metrics'].get(k) is not None and np.isfinite(r['units'][group]['metrics'][k]) for k in weights)]
  for row in valid:row['units'][group]['score']=0.
  for metric,weight in weights.items():
   values=np.array([r['units'][group]['metrics'][metric] for r in valid]);mean=values.mean() if len(values) else 0;sd=values.std() if len(values) else 0
   for row in valid:row['units'][group]['score']+=weight*(row['units'][group]['metrics'][metric]-mean)/sd if sd>0 else 0
  for row in valid:row['units'][group]['rank']=1+sum(other['units'][group]['score']>row['units'][group]['score']+1e-10 for other in valid)
 return result

def run():
 now=pd.Timestamp.now(tz='UTC');season=now.year if now.month>=3 else now.year-1;url=BASE+'stats_player/'+f'stats_player_week_{season}.csv.gz';raw,_=get(url+'?asof='+now.strftime('%Y%m%d%H'));stats=pd.read_csv(io.BytesIO(raw),compression='gzip',low_memory=False);teams=build(stats,season)
 if any(r['games']==0 for r in teams):raise ValueError('Incomplete 32-team season coverage; retaining previous rankings')
 payload={'generatedAt':now.isoformat(),'season':season,'throughWeek':int(max(r['throughWeek'] for r in teams)),'teams':teams,'labels':LABELS,'weights':WEIGHTS,'source':url,'methodology':['Ranks compare current-season regular-season production, not scouting grades or predicted future strength. Higher weighted standardized production scores rank better; missing metrics are unranked and ties share a rank.','QB combines passing and rushing EPA/play, net yards/play and turnover rate. RB combines EPA/opportunity, scrimmage yards/game and touchdowns/game. WR/TE combine EPA/target, receiving yards/game and touchdowns/game.','OL is a protection/run-game proxy: sack rate and RB rushing EPA/carry. Quarterback, backs and scheme also affect it; it is not an isolated blocking grade.','DL includes DE, DT, NT, DL, EDGE and OLB labels, ranked on sacks, tackles for loss and QB hits/game. Off-ball LB uses tackles for loss, passes defended, solo tackles and forced fumbles/game.','CB and safety rankings measure passes defended, interceptions and forced fumbles/game. They do not measure coverage quality or penalize unthrown targets. Players labeled only DB are excluded from CB/S because the subtype is unknown.','All players who recorded stats contribute to their actual team at the time. These are season unit results, not an injury-adjusted ranking of today’s starters. Per-game metrics use the team’s recorded games, not sums of individual appearances.']}
 from edge.pipeline import clean
 Path('data/position-rankings.json').write_text(json.dumps(clean(payload),separators=(',',':'),allow_nan=False));print(json.dumps({'teams':len(teams),'season':season,'throughWeek':payload['throughWeek'],'ranked':{k:sum(r['units'][k]['rank'] is not None for r in teams) for k in WEIGHTS}}))
if __name__=='__main__':run()
