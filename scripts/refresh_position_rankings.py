"""Current-season unit production, with exposure shrinkage, recent form and schedule context."""
import io,json
from pathlib import Path
import numpy as np
import pandas as pd
from edge.data import get,BASE,team
TEAMS='ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LAC LAR LV MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS'.split()
GROUPS={'QB':['QB'],'RB':['RB','HB','FB'],'WR':['WR'],'TE':['TE'],'DL':['DE','DT','NT','DL','EDGE','ED','OLB'],'LB':['LB','MLB','ILB'],'CB':['CB'],'S':['S','SAF','FS','SS']}
LABELS={'QB':'Quarterbacks','RB':'Running backs','WR':'Wide receivers','TE':'Tight ends','OL':'Offensive line','DL':'Defensive line / edge','LB':'Linebackers','CB':'Cornerbacks','S':'Safeties'}
WEIGHTS={'QB':{'epaPerPlay':.6,'yardsPerPlay':.15,'firstDownRate':.15,'turnoversPerPlay':-.1},'RB':{'yardsPerGame':.3,'firstDownsPerGame':.25,'touchdownsPerGame':.15,'epaPerGame':.15,'epaPerOpportunity':.15},'WR':{'yardsPerGame':.3,'firstDownsPerGame':.25,'touchdownsPerGame':.15,'epaPerGame':.15,'epaPerOpportunity':.15},'TE':{'yardsPerGame':.3,'firstDownsPerGame':.25,'touchdownsPerGame':.15,'epaPerGame':.15,'epaPerOpportunity':.15},'OL':{'sackRate':-.65,'rbRushEpaPerCarry':.35},'DL':{'sackRate':.45,'qbHitRate':.25,'tflRate':.3},'LB':{'tflRate':.35,'passesDefendedRate':.3,'forcedFumbleRate':.25,'soloTackleRate':.1},'CB':{'passesDefendedRate':.65,'interceptionRate':.25,'forcedFumbleRate':.1},'S':{'passesDefendedRate':.5,'interceptionRate':.3,'forcedFumbleRate':.2}}
METRICS={'yardsPerGame':{'label':'Yards / team game'},'firstDownsPerGame':{'label':'First downs / team game'},'touchdownsPerGame':{'label':'Touchdowns / team game'},'epaPerGame':{'label':'EPA / team game'},'epaPerOpportunity':{'label':'EPA / target or touch'},'epaPerPlay':{'label':'EPA / QB play'},'yardsPerPlay':{'label':'Net yards / QB play'},'firstDownRate':{'label':'First-down rate','format':'percent'},'turnoversPerPlay':{'label':'Turnover rate','format':'percent'},'sackRate':{'label':'Sacks / dropback','format':'percent'},'rbRushEpaPerCarry':{'label':'RB rush EPA / carry'},'qbHitRate':{'label':'QB hits / dropback','format':'percent'},'tflRate':{'label':'Tackles for loss / opposing play','format':'percent'},'passesDefendedRate':{'label':'Passes defended / opposing dropback','format':'percent'},'forcedFumbleRate':{'label':'Forced fumbles / opposing play','format':'percent'},'soloTackleRate':{'label':'Solo tackles / opposing play','format':'percent'},'interceptionRate':{'label':'Interceptions / opposing dropback','format':'percent'}}
RECENT_WEIGHT=.25
OPPONENT_WEIGHT=.35

def total(g,*keys):
 if g.empty:return None
 values=[]
 for key in keys:
  if key not in g:return None
  n=pd.to_numeric(g[key],errors='coerce').sum(min_count=1)
  if pd.isna(n):
   exposure_keys={'passing_epa':['attempts','sacks_suffered'],'rushing_epa':['carries'],'receiving_epa':['targets']}.get(key)
   exposure=total(g,*exposure_keys) if exposure_keys else None
   if exposure==0:n=0.
   else:return None
  values.append(float(n))
 return sum(values)

def game_units(own,opposing):
 result={};oppdb=total(opposing,'attempts','sacks_suffered');oppplays=total(opposing,'attempts','sacks_suffered','carries')
 for group,positions in GROUPS.items():
  g=own[own.position.isin(positions)];v=lambda *keys:total(g,*keys)
  if group=='QB':
   den=v('attempts','sacks_suffered','carries');values={'epaPerPlay':(v('passing_epa','rushing_epa'),den,100),'yardsPerPlay':(v('passing_yards','rushing_yards','sack_yards_lost'),den,100),'firstDownRate':(v('passing_first_downs','rushing_first_downs'),den,100),'turnoversPerPlay':(v('passing_interceptions','sack_fumbles_lost','rushing_fumbles_lost'),den,100)}
  elif group in ['RB','WR','TE']:
   rb=group=='RB';yards=v('rushing_yards','receiving_yards') if rb else v('receiving_yards');epa=v('rushing_epa','receiving_epa') if rb else v('receiving_epa');fd=v('rushing_first_downs','receiving_first_downs') if rb else v('receiving_first_downs');td=v('rushing_tds','receiving_tds') if rb else v('receiving_tds');den=v('carries','targets') if rb else v('targets');values={'yardsPerGame':(yards,1,3),'firstDownsPerGame':(fd,1,3),'touchdownsPerGame':(td,1,3),'epaPerGame':(epa,1,3),'epaPerOpportunity':(epa,den,40)}
  else:
   fields={'sackRate':('def_sacks',oppdb,100),'qbHitRate':('def_qb_hits',oppdb,100),'tflRate':('def_tackles_for_loss',oppplays,150),'passesDefendedRate':('def_pass_defended',oppdb,100),'forcedFumbleRate':('def_fumbles_forced',oppplays,150),'soloTackleRate':('def_tackles_solo',oppplays,150),'interceptionRate':('def_interceptions',oppdb,100)};values={key:(v(fields[key][0]),fields[key][1],fields[key][2]) for key in WEIGHTS[group]}
  result[group]={'values':values,'players':set(g.player_id)}
 backs=own[own.position.isin(GROUPS['RB'])];result['OL']={'values':{'sackRate':(total(own,'sacks_suffered'),total(own,'attempts','sacks_suffered'),100),'rbRushEpaPerCarry':(total(backs,'rushing_epa'),total(backs,'carries'),60)},'players':set()}
 return result

def paired(rows,group,metric):
 return [(r['units'][group]['values'][metric],r) for r in rows if r['units'][group]['values'].get(metric) and all(v is not None and np.isfinite(v) for v in r['units'][group]['values'][metric][:2]) and r['units'][group]['values'][metric][1]>0]

def feature(rows,league_rows,group,metric,club):
 pairs=paired(rows,group,metric);pool=paired(league_rows,group,metric)
 if not pairs or not pool:return None
 num=sum(v[0] for v,_ in pairs);den=sum(v[1] for v,_ in pairs);prior=pairs[0][0][2];league=sum(v[0] for v,_ in pool)/sum(v[1] for v,_ in pool);reference=[(v,r) for v,r in pool if r['team']!=club and r['opponent']!=club];reference_rate=sum(v[0] for v,_ in reference)/sum(v[1] for v,_ in reference) if reference else league;expected=0.;matched=0
 for v,row in pairs:
  others=[(a,b) for a,b in pool if row['opponent'] and b['opponent']==row['opponent'] and b['team']!=club]
  other_den=sum(a[1] for a,_ in others);baseline=(sum(a[0] for a,_ in others)+prior*reference_rate)/(other_den+prior)
  if other_den>0:matched+=1
  expected+=baseline*v[1]/den
 raw=num/den;shrunk=(num+prior*league)/(den+prior)
 return {'raw':raw,'numerator':num,'exposure':den,'priorExposure':prior,'reliability':den/(den+prior),'leagueBaseline':league,'opponentExpected':expected,'opponentLeagueBaseline':reference_rate,'opponentGames':matched,'opportunityGames':len(pairs),'games':sum(1 for row in rows if all(v is not None and np.isfinite(v) for v in row['units'][group]['values'][metric][:2])),'adjusted':shrunk-OPPONENT_WEIGHT*(expected-reference_rate)}

def build(stats,season):
 d=stats[(stats.season==season)&(stats.season_type=='REG')&stats.week.gt(0)].copy();d['team']=d.team.map(team)
 if 'opponent_team' not in d:d['opponent_team']=None
 if d.duplicated(['player_id','game_id','team']).any():raise ValueError('Duplicate player-game statistics')
 records=[]
 for (club,gid),own in d.groupby(['team','game_id']):
  opponents=own.opponent_team.dropna().map(team).unique();opponent=opponents[0] if len(opponents)==1 else None;opposing=d[(d.game_id==gid)&(d.team==opponent)] if opponent else d.iloc[:0]
  records.append({'team':club,'gameId':gid,'week':int(own.week.max()),'opponent':opponent,'units':game_units(own,opposing)})
 result=[]
 for club in TEAMS:
  own=sorted([r for r in records if r['team']==club],key=lambda r:(r['week'],r['gameId']));recent=own[-4:];units={}
  for group,weights in WEIGHTS.items():
   evidence={};inputs={};metrics={}
   for metric in weights:
    season_value=feature(own,records,group,metric,club);recent_value=feature(recent,records,group,metric,club)
    if season_value is None or recent_value is None:continue
    value=(1-RECENT_WEIGHT)*season_value['adjusted']+RECENT_WEIGHT*recent_value['adjusted'];exposure_unit='team games' if metric.endswith('PerGame') else 'targets' if group in ['WR','TE'] else 'carries + targets' if group=='RB' else 'QB plays' if group=='QB' else ('dropbacks' if metric=='sackRate' else 'RB carries') if group=='OL' else ('opposing dropbacks' if metric in ['sackRate','qbHitRate','passesDefendedRate','interceptionRate'] else 'opposing plays');evidence[metric]={'exposureUnit':exposure_unit,'season':season_value,'recent':recent_value,'input':value,'weight':weights[metric]};metrics[metric]=season_value['raw'];inputs[metric]=value
   units[group]={'metrics':metrics,'inputs':inputs,'evidence':evidence,'players':len(set().union(*(r['units'][group]['players'] for r in own))) if own else 0,'rank':None,'score':None,'partialMetrics':[k for k,e in evidence.items() if e['season']['games']<len(own)],'sampleGames':len(own),'recentGames':len(recent),'proxy':group=='OL'}
  result.append({'team':club,'games':len(own),'throughWeek':max((r['week'] for r in own),default=None),'units':units})
 for group,weights in WEIGHTS.items():
  valid=[r for r in result if all(k in r['units'][group]['inputs'] for k in weights)]
  for row in valid:row['units'][group]['score']=0.
  for metric,weight in weights.items():
   values=np.array([r['units'][group]['inputs'][metric] for r in valid]);mean=values.mean() if len(values) else 0;sd=values.std() if len(values) else 0
   for row in valid:
    z=float(np.clip((row['units'][group]['inputs'][metric]-mean)/sd,-2.5,2.5)) if sd>0 else 0.;row['units'][group]['score']+=weight*z;row['units'][group]['evidence'][metric]['contribution']=weight*z
  for row in valid:row['units'][group]['rank']=1+sum(other['units'][group]['score']>row['units'][group]['score']+1e-10 for other in valid)
  if valid:
   rng=np.random.default_rng(17);keys=list(weights);z=np.array([[r['units'][group]['evidence'][key]['contribution']/weights[key] for key in keys] for r in valid]);base=np.array([weights[key] for key in keys]);ranks=[[r['units'][group]['rank']] for r in valid]
   for _ in range(200):
    varied=base*rng.uniform(.8,1.2,len(keys));varied=varied/np.abs(varied).sum();scores=z@varied
    for i,score in enumerate(scores):ranks[i].append(1+int(np.sum(scores>score+1e-10)))
   for i,row in enumerate(valid):row['units'][group]['weightSensitivity']={'low':min(ranks[i]),'high':max(ranks[i]),'scenarios':201,'definition':'Observed rank range across baseline plus 200 reproducible ±20% component-weight perturbations. Not a statistical confidence interval.'}
 return result

def run():
 now=pd.Timestamp.now(tz='UTC');season=now.year if now.month>=3 else now.year-1;url=BASE+'stats_player/'+f'stats_player_week_{season}.csv.gz';raw,_=get(url+'?asof='+now.strftime('%Y%m%d%H'));stats=pd.read_csv(io.BytesIO(raw),compression='gzip',low_memory=False);teams=build(stats,season)
 if any(r['games']==0 for r in teams):raise ValueError('Incomplete 32-team season coverage; retaining previous rankings')
 path=Path('data/position-rankings.json');previous=json.loads(path.read_text()) if path.exists() else {};lookup={r['team']:r for r in previous.get('teams',[])}
 for row in teams:
  for group,unit in row['units'].items():
   old=lookup.get(row['team'],{}).get('units',{}).get(group,{})
   unit['previousRank']=old.get('rank') if previous.get('season')==season else None
 payload={'schemaVersion':2,'methodologyVersion':'opportunity-schedule-recent-v2','generatedAt':now.isoformat(),'season':season,'throughWeek':int(max(r['throughWeek'] for r in teams)),'teams':teams,'labels':LABELS,'weights':WEIGHTS,'metricLabels':METRICS,'source':url,'methodology':['Descriptive current-season regular-season production, not scouting grades or a validated forecast. No team-specific overrides. Missing inputs stay unranked; ties share a rank.','Missing positive-exposure values remain missing. EPA is zero only when its underlying recorded opportunities are explicitly zero. Partial metric game coverage is disclosed in each rank’s evidence.','Every metric uses 75% full-season evidence and 25% the team’s last four recorded games (overlapping samples, not independent tests). All roster contributors are included on the team where they played.','Rate estimates shrink toward the league baseline with 40 target/touch equivalents, 100 dropbacks/QB plays or 150 opposing plays. Per-game totals use a three-game prior; OL rushing efficiency uses 60 carries. Small samples therefore cannot dominate through an extreme raw rate.','Opponent baselines use the same positional group’s performance against each opponent in its OTHER games, excluding every game involving the evaluated team. Opponent baselines are themselves shrunk. We remove 35% of the difference between expected opposition and the league baseline; this is a conservative descriptive adjustment, not a causal isolation of talent.','Weight sensitivity shows the observed rank range across the baseline and 200 reproducible ±20% relative component-weight perturbations, with weights renormalized. It tests dependence on weighting choices, not predictive accuracy, sampling uncertainty or every possible weighting.','Score inputs are standardized across eligible teams and clipped to ±2.5 standard deviations before weighting. Click a rank for its raw season/recent values, opponent baseline, sample exposure and score contributions.','WR/TE/RB: 30% yards/game, 25% first downs/game, 15% TD/game, 15% total EPA/game, 15% EPA/opportunity. Efficiency no longer outweighs sustained production; receiving EPA cannot receive a 50% standalone weight.','QB: 60% EPA/play, 15% net yards/play, 15% first-down rate, 10% turnover avoidance, including QB rushing and sacks. OL: 65% sack avoidance and 35% RB rushing EPA/carry; it remains a QB/back/scheme-influenced proxy, not an isolated blocking grade.','Defense is normalized for opposing dropbacks or plays, rather than games alone. DL includes DE/DT/NT/DL/EDGE/OLB labels. Off-ball LB includes LB/MLB/ILB. Generic DB labels remain excluded from CB/S.','DL: sacks, QB hits and tackles for loss. LB: tackles for loss, passes defended, forced fumbles and a small solo-tackle component. CB/S: passes defended, interceptions and forced fumbles. Individual targets allowed, coverage snaps, missed tackles and blocking grades are unavailable here: these remain production indices, not complete position-quality ratings.','Season results do not automatically predict the strength of today’s injury-adjusted starters. Schedule adjustments use all currently available season outcomes; these are not historical point-in-time backtests.']}
 from edge.pipeline import clean
 path.write_text(json.dumps(clean(payload),separators=(',',':'),allow_nan=False));print(json.dumps({'teams':len(teams),'season':season,'throughWeek':payload['throughWeek'],'ranked':{k:sum(r['units'][k]['rank'] is not None for r in teams) for k in WEIGHTS},'tightEnds':{r['team']:r['units']['TE'] for r in teams if r['team'] in ['ARI','KC']}}))
if __name__=='__main__':run()
