"""Weekly, point-in-time ATTD research from public NFL play-by-play and actual prices."""
import json,math,os,calendar
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss,log_loss
from .data import normalize_stats,add_snap_zeros,schedule_rows,team
from .context import parquet_asset
from .markets import FULL_NAMES
from .pipeline import clean
ROOT=Path(__file__).resolve().parents[1]
PBP=['game_id','play_id','season','season_type','week','posteam','defteam','play_type','yardline_100','rusher_player_id','receiver_player_id','rush_attempt','pass_attempt','qb_dropback','qb_kneel','qb_spike','rush_touchdown','pass_touchdown','return_touchdown','epa','success','score_differential','qtr','game_seconds_remaining','drive','pass_oe','air_yards','complete_pass','touchdown','td_player_id']
OPPS=['carries','targets','rzCarries','rzTargets','i10Carries','i5Carries','i5Targets','rzTouches','rzOpportunities','xTD','td']
FEATURES=['xTD_last4','rzTouches_last4','i5Carries_last4','i5Targets_last4','carries_last4','targets_last4','td_last4','rzShare_last4','i10RushShare_last4','oppPositionTD_last6','oppRZEpa_last6','teamTD_last6','position_code']
def load_json(name):
 try:return json.loads((ROOT/'data'/name).read_text())
 except (OSError,ValueError):return {}
def scoring_opportunities(pbp,positions,calibration_season):
 d=pbp.copy();d=d[d.season_type.eq('REG') & d.play_type.isin(['run','pass'])];d=d[~d.qb_kneel.eq(1)&~d.qb_spike.eq(1)&d.yardline_100.between(1,100)];pieces=[]
 for kind,pid,flag,outcome in [('rush','rusher_player_id','rush_attempt','rush_touchdown'),('target','receiver_player_id','pass_attempt','pass_touchdown')]:
  g=d[d[pid].notna()&d[flag].eq(1)].copy();g['player_id']=g[pid];g['kind']=kind;g['scored']=g[outcome].fillna(0).clip(0,1);pieces.append(g)
 o=pd.concat(pieces,ignore_index=True);o['position']=o.player_id.map(positions).fillna('OTHER');o['distanceBin']=pd.cut(o.yardline_100,[0,5,10,20,30,50,100],labels=False);training=o[o.season<calibration_season]
 broad=training.groupby(['kind','distanceBin']).scored.agg(['sum','count']);specific=training.groupby(['kind','position','distanceBin']).scored.agg(['sum','count']);rates={}
 for (kind,pos,dist),g in o.groupby(['kind','position','distanceBin']):
  base=broad.loc[(kind,dist)] if (kind,dist) in broad.index else None;prior=base['sum']/base['count'] if base is not None and base['count'] else .01;small=specific.loc[(kind,pos,dist)] if (kind,pos,dist) in specific.index else None
  rates[(kind,pos,dist)]=(small['sum']+30*prior)/(small['count']+30) if small is not None else prior
 o['xTD']=[rates[(r.kind,r.position,r.distanceBin)] for r in o.itertuples()]
 for name,mask in [('carries',o.kind.eq('rush')),('targets',o.kind.eq('target')),('rzCarries',o.kind.eq('rush')&o.yardline_100.le(20)),('rzTargets',o.kind.eq('target')&o.yardline_100.le(20)),('i10Carries',o.kind.eq('rush')&o.yardline_100.le(10)),('i5Carries',o.kind.eq('rush')&o.yardline_100.le(5)),('i5Targets',o.kind.eq('target')&o.yardline_100.le(5))]:o[name]=mask.astype(int)
 o['rzOpportunities']=o.rzCarries+o.rzTargets;o['rzTouches']=o.rzCarries+((o.kind.eq('target'))&o.yardline_100.le(20)&o.complete_pass.eq(1)).astype(int);o['td']=o.scored
 return o,d

def build_frame(stats,schedules,opportunities,plays,now,current_teams=None):
 actual=stats.drop(columns=['game_id','opponent_team'],errors='ignore').merge(schedules,on=['season','week','team'],validate='many_to_one');actual=actual[actual.completed&(actual.kickoff<now)&actual.game_id.isin(opportunities.game_id.unique())].copy()
 totals=opportunities.groupby(['game_id','player_id'])[OPPS].sum().reset_index();actual=actual.merge(totals,on=['game_id','player_id'],how='left',suffixes=('_stats',''))
 for k in OPPS:actual[k]=actual[k].fillna(0)
 # The settlement target is rushing + receiving TDs. A QB's passing TD is NOT an ATTD.
 actual['actualTD']=(actual.rushing_tds.fillna(0)+actual.receiving_tds.fillna(0)).gt(0).astype(int)
 team_opps=opportunities.groupby(['game_id','posteam'])[['rzTargets','i10Carries','rzTouches','td']].sum().rename(columns=lambda k:'team_'+k).reset_index().rename(columns={'posteam':'team'})
 actual=actual.merge(team_opps,on=['game_id','team'],how='left');actual['rzShare']=actual.rzTargets/actual.team_rzTargets.replace(0,np.nan);actual['i10RushShare']=actual.i10Carries/actual.team_i10Carries.replace(0,np.nan)
 schedule_future=schedules[(schedules.kickoff>now)&(schedules.kickoff<=now+pd.Timedelta(days=8))].sort_values('kickoff').drop_duplicates('team')
 latest=actual[actual.kickoff>=now-pd.Timedelta(days=35)].sort_values('kickoff').groupby('player_id').tail(1)[['player_id','player_display_name','position','team']]
 if current_teams:latest['team']=latest.player_id.map(current_teams).fillna(latest.team)
 future=latest.merge(schedule_future,on='team');future['forecast']=True;actual['forecast']=False;d=pd.concat([actual,future],ignore_index=True).sort_values(['kickoff','player_id'])
 d['priorGames']=d.groupby('player_id').cumcount()
 for k in ['xTD','rzTouches','i5Carries','i5Targets','carries','targets','td','rzShare','i10RushShare']:d[k+'_last4']=d.groupby('player_id')[k].transform(lambda s:s.shift(1).rolling(4,min_periods=1).mean())
 d['position_code']=d.position.map({'QB':0,'RB':1,'WR':2,'TE':3})
 # Defense and team contexts use completed, published games strictly before kickoff.
 pos=actual.groupby(['game_id','opponent_team','position','kickoff'],as_index=False).agg(td=('td','sum'));team_history=actual.groupby(['game_id','team','kickoff'],as_index=False).agg(td=('td','sum'))
 rz=plays[plays.yardline_100.le(20)].groupby(['game_id','defteam'],as_index=False).agg(rzEPA=('epa','mean'))
 def_hist=schedules[schedules.completed&(schedules.kickoff<now)][['game_id','team','kickoff']].merge(rz,left_on=['game_id','team'],right_on=['game_id','defteam'],how='left')
 records=[]
 for r in d[['game_id','team','opponent_team','position','kickoff']].drop_duplicates().itertuples():
  dh=def_hist[(def_hist.team==r.opponent_team)&(def_hist.kickoff<r.kickoff)].sort_values('kickoff').tail(6);ids=set(dh.game_id);ph=pos[(pos.opponent_team==r.opponent_team)&pos.position.eq(r.position)&pos.game_id.isin(ids)];th=team_history[(team_history.team==r.team)&(team_history.kickoff<r.kickoff)].sort_values('kickoff').tail(6)
  records.append({'game_id':r.game_id,'team':r.team,'position':r.position,'oppPositionTD_last6':ph.td.sum()/len(ids) if ids else np.nan,'oppRZEpa_last6':dh.rzEPA.mean(),'teamTD_last6':th.td.mean()})
 d=d.merge(pd.DataFrame(records),on=['game_id','team','position'],validate='many_to_one');return d,actual

def fit_model(d):return make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),StandardScaler(),LogisticRegression(C=.25,max_iter=700)).fit(d[FEATURES],d.actualTD)
def evaluate(frame,season):
 d=frame[(~frame.forecast)&frame.priorGames.ge(3)&(frame.carries_last4+frame.targets_last4).ge(1)];pred=[];folds=[]
 for week in sorted(d[d.season.eq(season)].week.unique()):
  train=d[(d.season<season)|((d.season==season)&(d.week<week))];test=d[d.season.eq(season)&d.week.eq(week)]
  if len(train)<500 or len(test)<10:continue
  m=fit_model(train);p=m.predict_proba(test[FEATURES])[:,1];base=test.position.map(train.groupby('position').actualTD.mean()).fillna(train.actualTD.mean()).to_numpy();folds.append({'week':int(week),'n':len(test),'brier':brier_score_loss(test.actualTD,p),'baselineBrier':brier_score_loss(test.actualTD,base)})
  pred.extend({'p':float(a),'actual':int(b),'baseline':float(c)} for a,b,c in zip(p,test.actualTD,base))
 if not pred:raise ValueError('Insufficient current-season ATTD test data')
 y=np.array([r['actual'] for r in pred]);p=np.array([r['p'] for r in pred]);b=np.array([r['baseline'] for r in pred]);bins=[]
 for lo in np.arange(0,1,.1):
  mask=(p>=lo)&(p<lo+.1)
  if mask.sum():bins.append({'n':int(mask.sum()),'estimated':float(p[mask].mean()),'observed':float(y[mask].mean())})
 score=brier_score_loss(y,p);baseline=brier_score_loss(y,b);gap=max([abs(r['estimated']-r['observed']) for r in bins if r['n']>=50] or [1.]);return {'n':len(y),'brier':score,'baselineBrier':baseline,'logLoss':log_loss(y,p,labels=[0,1]),'calibration':bins,'folds':folds,'validationPassed':bool(len(y)>=500 and score<baseline and gap<=.12),'calibrationGap':gap,'scope':'Current-season expanding-week tests; preseason distance/type xTD calibration, final-corrected public files, no historical sportsbook ROI test.'},fit_model(d)
def american(p):return round(-100*p/(1-p)) if .5<=p<1 else round(100*(1-p)/p) if 0<p<.5 else None
def attd_price(outcome):
 # The Odds API's Yes/No prop uses player in description. Direct name outcomes also supported.
 name=str(outcome.get('name',''));description=outcome.get('description');return (description if name.lower()=='yes' else name if name.lower() not in ['no','over','under','yes'] else None)
def matched_quotes(player,game,odds,now,probability,validation,health):
 result=[]
 for event in odds.get('data',[]):
  if event.get('home_team')!=FULL_NAMES.get(game.home_team) or event.get('away_team')!=FULL_NAMES.get(game.away_team):continue
  if abs((pd.Timestamp(event['commence_time'])-game.kickoff).total_seconds())>=3600:continue
  for book in event.get('bookmakers',[]):
   for market in book.get('markets',[]):
    if market.get('key')!='player_anytime_td':continue
    for out in market.get('outcomes',[]):
     name=attd_price(out)
     if not name or ''.join(c for c in name.lower() if c.isalnum())!=''.join(c for c in player['name'].lower() if c.isalnum()):continue
     price=out.get('price');stamp=market.get('last_update') or book.get('last_update')
     if not isinstance(price,(int,float)) or abs(price)<100:continue
     decimal=1+price/100 if price>0 else 1+100/-price;ev=probability*decimal-1;age=(now-pd.Timestamp(stamp)).total_seconds() if stamp else math.inf;flags=[]
     if not 0<=age<=180:flags.append('stale or missing price time')
     if not validation['validationPassed']:flags.append('ATTD validation gate failed')
     if probability<.7:flags.append('estimated win probability below 70%')
     if not health.get('confirmed') or health.get('reviewRequired'):flags.append('availability not confirmed')
     health_time=pd.to_datetime(health.get('observedAt'),utc=True,errors='coerce')
     if pd.isna(health_time) or not 0<=(now-health_time).total_seconds()<=172800:flags.append('availability snapshot stale or missing')
     conservative=max(0,probability-validation['calibrationGap'])*decimal-1
     if conservative<.03:flags.append('sensitivity-adjusted value below 3%')
     if game.kickoff<=now:flags.append('game already started')
     result.append({'book':book['title'],'price':price,'line':'Anytime TD — Yes','impliedProbability':1/decimal,'estimatedReturn':ev,'conservativeReturn':conservative,'updatedAt':stamp,'flags':flags,'qualified':not flags})
 return sorted(result,key=lambda r:('stale or missing price time' not in r['flags'],r['estimatedReturn']),reverse=True)

def game_context(game,odds):
 for event in odds.get('data',[]):
  if event.get('home_team')!=FULL_NAMES.get(game.home_team) or event.get('away_team')!=FULL_NAMES.get(game.away_team):continue
  if abs((pd.Timestamp(event['commence_time'])-game.kickoff).total_seconds())>=3600:continue
  for book in event.get('bookmakers',[]):
   markets={m['key']:m for m in book.get('markets',[])};total=next((r.get('point') for r in markets.get('totals',{}).get('outcomes',[]) if r.get('name')=='Over'),None);spread=next((r.get('point') for r in markets.get('spreads',{}).get('outcomes',[]) if r.get('name')==FULL_NAMES.get(game.home_team)),None)
   if isinstance(total,(int,float)) and isinstance(spread,(int,float)):return {'book':book['title'],'total':total,'homeSpread':spread,'homeImpliedPoints':(total-spread)/2,'awayImpliedPoints':(total+spread)/2,'updatedAt':markets['totals'].get('last_update'),'note':'Implied points include field goals and extra points; points / 7 is not an expected-touchdown forecast.'}
 return {'note':'No matched same-book spread/total snapshot; implied team totals are unavailable.'}

def report(out=ROOT/'data',now=None):
 import nflreadpy as nfl
 now=pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now);season=now.year if now.month>=3 else now.year-1;years=list(range(2021,season+1));schedule=nfl.load_schedules(years).to_pandas();schedules=schedule_rows(schedule);stats=normalize_stats(nfl.load_player_stats(years).to_pandas(),positions=['QB','RB','WR','TE']);people=nfl.load_players().to_pandas();stats,_=add_snap_zeros(stats,nfl.load_snap_counts(years).to_pandas(),people)
 positions=stats.sort_values(['season','week']).groupby('player_id').position.last().to_dict();plays=pd.concat([parquet_asset('pbp',f'play_by_play_{year}.parquet',PBP,ROOT/'work/attd-pbp',immutable=year<season) for year in years],ignore_index=True);plays['posteam']=plays.posteam.map(team);plays['defteam']=plays.defteam.map(team)
 opportunities,valid_plays=scoring_opportunities(plays,positions,season);availability=load_json('availability.json');bundle=load_json('latest.json');current_teams={p['playerId']:p['team'] for p in bundle.get('players',[])};current_teams.update({r['playerId']:r['team'] for r in availability.get('roster',[]) if r.get('fresh')});frame,actual=build_frame(stats,schedules,opportunities,valid_plays,now,current_teams);validation,model=evaluate(frame,season);
 from .td_order import evaluate_and_predict
 order_validation,all_player_odds=evaluate_and_predict(frame,plays,season)
 eligible_future=frame[frame.forecast&frame.priorGames.ge(3)&(frame.carries_last4+frame.targets_last4).ge(1)]
 if len(eligible_future):
  for row,prob in zip(eligible_future.itertuples(),model.predict_proba(eligible_future[FEATURES])[:,1]):all_player_odds.setdefault(row.player_id,{'gameId':row.game_id,'kickoff':row.kickoff.isoformat(),'team':row.team,'opponent':row.opponent_team,'markets':{}})['markets']['player_anytime_td']={'probability':float(prob),'fairOdds':american(prob),'validationPassed':validation['validationPassed'],'status':'model estimate' if validation['validationPassed'] else 'research estimate'}
 for profile in [*bundle.get('players',[]),*availability.get('roster',[])]:
  pid=profile['playerId'];entry=all_player_odds.setdefault(pid,{'team':profile.get('team'),'markets':{},'status':'unavailable','reason':'No eligible upcoming forecast: requires a scheduled game, three prior recorded games and at least one recent carry/target per game'})
  if availability.get('injuries',{}).get(pid,{}).get('ruledOut'):entry.update(markets={},status='unavailable',reason='Ruled out; no participation-conditional odds offered')
 roles={r['playerId']:r for r in availability.get('roster',[])};profiles={p['playerId']:p for p in bundle.get('players',[])};health=availability.get('injuries',{});odds=load_json('attd-odds.json');game_odds=load_json('game-odds.json');future=schedules[schedules.home.eq(1)&schedules.kickoff.gt(now)].sort_values('kickoff');week=int(future.iloc[0].week) if len(future) else int(schedules[schedules.season.eq(season)].week.max());week_games=schedules[schedules.season.eq(season)&schedules.week.eq(week)&schedules.home.eq(1)].sort_values('kickoff');games=[]
 season_actual=actual[actual.season.eq(season)]
 position_totals=season_actual.groupby(['opponent_team','position']).td.sum()
 defender_games=season_actual.groupby('opponent_team').game_id.nunique()
 ranks={}
 for position in ['QB','RB','WR','TE']:
  allowed=pd.Series({club:position_totals.get((club,position),0)/max(1,n) for club,n in defender_games.items()});ranks[position]=allowed.rank(ascending=False,method='min').to_dict()
 from .td_archive import retain_pregame_game
 try:previous=json.loads((out/'touchdown-research.json').read_text())
 except (OSError,ValueError):previous={}
 for game in week_games.itertuples():
  if game.kickoff<=now:
   archived=retain_pregame_game(previous,game.game_id,game.kickoff.isoformat())
   if archived is None:archived=retain_pregame_game(load_json('touchdown-pregame-archive.json'),game.game_id,game.kickoff.isoformat())
   games.append(archived or {'gameId':game.game_id,'homeTeam':game.home_team,'awayTeam':game.away_team,'kickoff':game.kickoff.isoformat(),'status':'started/completed','candidates':[],'note':'No archived pregame projections available; no retrospective picks generated.'})
   continue
  context=game_context(game,game_odds);candidates=[];team_context={}
  for club,opponent in [(game.home_team,game.away_team),(game.away_team,game.home_team)]:
   recent_schedule=schedules[schedules.team.eq(club)&schedules.completed&(schedules.kickoff<game.kickoff)&schedules.game_id.isin(opportunities.game_id.unique())].sort_values('kickoff').tail(4);ids=set(recent_schedule.game_id);o=opportunities[opportunities.posteam.eq(club)&opportunities.game_id.isin(ids)];team_tot=o[OPPS].sum();team_rz=valid_plays[valid_plays.posteam.eq(club)&valid_plays.game_id.isin(ids)&valid_plays.yardline_100.le(20)];neutral=valid_plays[valid_plays.posteam.eq(club)&valid_plays.game_id.isin(ids)&valid_plays.qtr.le(3)&valid_plays.score_differential.abs().le(8)].sort_values(['game_id','play_id']);gap=neutral.groupby(['game_id','drive']).game_seconds_remaining.diff()*-1;pace=gap[gap.between(1,60)].mean();opp_games=schedules[schedules.team.eq(opponent)&schedules.completed&(schedules.kickoff<game.kickoff)].sort_values('kickoff').tail(6);opp_ids=set(opp_games.game_id);def_plays=valid_plays[valid_plays.defteam.eq(opponent)&valid_plays.game_id.isin(opp_ids)];rz_def=def_plays[def_plays.yardline_100.le(20)]
   team_context[club]={'lastGames':len(ids),'rzPassRate':team_rz.qb_dropback.mean(),'rzPassOverExpectedPercentagePoints':team_rz.pass_oe.mean(),'neutralSecondsPerPlay':pace,'opponentRZSuccessAllowed':rz_def.epa.gt(0).mean(),'opponentRZEPA':rz_def.epa.mean(),'opponentPassEPA':def_plays[def_plays.qb_dropback.eq(1)].epa.mean(),'opponentRushEPA':def_plays[def_plays.rush_attempt.eq(1)].epa.mean(),'goalLineRushTDConversion':o[(o.kind.eq('rush'))&o.yardline_100.le(5)].scored.mean(),'opponentGoalLineRushTDConversionAllowed':def_plays[def_plays.rush_attempt.eq(1)&def_plays.yardline_100.le(5)].rush_touchdown.mean(),'scenario':'Trailing teams can shift toward targets; leading teams toward carries. These are conditional scenarios, not asserted second-half outcomes.','lineMatchup':'Current ESPN block-win rates, licensed PFF grades, adjusted line yards and slot/perimeter alignment splits are unavailable; no invented grading or coverage adjustment is applied.'}
   f=frame[frame.forecast&frame.team.eq(club)&frame.priorGames.ge(3)&(frame.carries_last4+frame.targets_last4).ge(1)]
   if f.empty:continue
   probabilities=model.predict_proba(f[FEATURES])[:,1]
   for (_,r),prob in zip(f.iterrows(),probabilities):
    pid=r.player_id;role=roles.get(pid,{});h=health.get(pid,{});profile=profiles.get(pid,{});current_team=role.get('team') if role.get('fresh') else profile.get('team',r.team)
    if current_team!=club or h.get('ruledOut') or role and not role.get('expectedStarter') and r.carries_last4+r.targets_last4<4:continue
    stats_player=o[o.player_id.eq(pid)][OPPS].sum();item={'playerId':pid,'name':r.player_display_name,'position':r.position,'team':club,'opponent':opponent,'probability':float(prob),'fairOdds':american(prob),'health':{'label':h.get('label','Availability unconfirmed'),'confirmed':h.get('confirmed',False),'reviewRequired':h.get('reviewRequired',False)},'recent':{k:float(stats_player[k]) for k in OPPS},'games':len(ids),'rzTargetShare':float(stats_player.rzTargets/team_tot.rzTargets) if team_tot.rzTargets else None,'i10RushShare':float(stats_player.i10Carries/team_tot.i10Carries) if team_tot.i10Carries else None,'xTDminusActual':float(stats_player.xTD-stats_player.td),'opponentPositionTDPerGame':float(r.oppPositionTD_last6),'opponentPositionTDRankSeason':ranks.get(r.position,{}).get(opponent),'opponentPositionTDRankTeams':len(defender_games),'coverage':next(({'manRate':v['features'].get('matchup_man_rate'),'zoneRate':v['features'].get('matchup_zone_rate'),'scope':bundle.get('enrichment',{}).get('coverageBacktestScope')} for v in bundle.get('forecasts',[]) if v.get('playerId')==pid),{})}
    item['quotes']=matched_quotes(item,game,odds,now,float(prob),validation,h);candidates.append(item)
  ranked=sorted(candidates,key=lambda p:p['probability'],reverse=True);selected=[]
  if ranked:selected.append({**ranked[0],'risk':'Core research · highest estimated probability'})
  value=sorted([p for p in candidates if p['probability']>=.10 and p['recent']['rzOpportunities']>=2 and p['quotes'] and p['quotes'][0]['estimatedReturn']>0 and (not selected or p['playerId']!=selected[0]['playerId'])],key=lambda p:p['quotes'][0]['estimatedReturn'],reverse=True)
  if value:selected.append({**value[0],'risk':'High-yield research · positive price estimate'})
  for p in ranked:
   if len(selected)>=3:break
   if not any(s['playerId']==p['playerId'] for s in selected):selected.append({**p,'risk':'Additional research candidate'})
  games.append({'gameId':game.game_id,'homeTeam':game.home_team,'awayTeam':game.away_team,'kickoff':game.kickoff.isoformat(),'status':'upcoming','context':context,'teams':team_context,'candidates':selected,'players':ranked,'note':'Core is a relative probability ranking, not a guaranteed bet. High-yield requires an actual positive-value price; qualification still needs all gates including ≥70% win estimate.'})
 payload=clean({'schemaVersion':1,'generatedAt':now.isoformat(),'season':season,'week':week,'games':games,'validation':validation,'orderValidation':order_validation,'allPlayerOdds':all_player_odds,'oddsCoverage':{k:v for k,v in odds.items() if k!='data'},'dataQuality':{'completedCurrentSeasonGamesMissingPBP':sorted(set(schedules[schedules.season.eq(season)&schedules.completed&(schedules.kickoff<now)].game_id)-set(opportunities.game_id))},'methodology':['ATTD counts rushing and receiving TDs, excluding QB passing TDs, return TDs and fumble-recovery scores; check individual book rules.','Distance/type/position expected-TD conversion calibrated only on seasons before the current season, with 30-opportunity smoothing.','Logistic player-game probability uses prior opportunity, high-value shares, team scoring and opponent-position/RZ context; evaluated by whole current-season weeks.','Recent volume uses four prior published team games, not an inferred future role; positive xTD minus actual is a regression signal, not a promise.','Implied team totals are contextual; no arbitrary points/7 TD assumption or fabricated offensive-line grades.','All recommendations remain research until current odds, availability and model gates are satisfied.','Feeds contain final stat corrections, not archived pregame data vintages. Missing published players/charting/odds are disclosed.'],'orderMethodology':'First and last TD fair odds come from separate player-game models trained on actual first/last scorer IDs, including defensive/return TDs in the event order and overtime. They use lagged opportunity and prior scoring-order rates; ATTD probabilities are not reused as first/last estimates. Game-level probability caps reserve mass for unmodeled scorers and no-TD outcomes. Book settlement rules may differ.','sources':[{'name':'nflverse public PBP, player stats, schedules and snaps','url':'https://github.com/nflverse/nflverse-data/releases'},{'name':'The Odds API ATTD Yes/No market','url':'https://the-odds-api.com/sports-odds-data/betting-markets.html'},{'name':'Official team reports / ESPN via public availability pipeline','url':'https://www.nfl.com/injuries/'}]})
 out.mkdir(exist_ok=True,parents=True);(out/'touchdown-research.json').write_text(json.dumps(payload,separators=(',',':'),allow_nan=False));write_markdown(payload,out/'touchdown-research.md');print(json.dumps({'week':week,'games':len(games),'upcoming':sum(g['status']=='upcoming' for g in games),'validation':validation},indent=2));return payload

def write_markdown(report,path):
 lines=[f"# Week {report['week']} Anytime Touchdown Research",f"Generated {report['generatedAt']}",f"Current-season tests: {report['validation']['n']}; Brier {report['validation']['brier']:.4f} vs baseline {report['validation']['baselineBrier']:.4f}."]
 for g in report['games']:
  lines+=['',f"## {g['awayTeam']} at {g['homeTeam']}",g['kickoff']]
  if g['status']!='upcoming':lines+=[g['note']];continue
  lines+=['### 1. Red zone & opportunity']
  for p in g['candidates']:
   r=p['recent'];lines+=[f"- {p['name']} ({p['team']} {p['position']}): {int(r['rzCarries'])} RZ carries, {int(r['rzTargets'])} RZ targets, {int(r['i5Carries'])} inside-5 carries, {int(r['i5Targets'])} inside-5 targets across {p['games']} team games; xTD {r['xTD']:.2f}, actual TD {r['td']:.0f}."]
  lines+=['### 2. Position matchup & leverage']
  for t,c in g['teams'].items():lines+=[f"- {t}: opponent RZ EPA {c['opponentRZEPA']}; pass EPA {c['opponentPassEPA']}; rush EPA {c['opponentRushEPA']}. {c['lineMatchup']}"]
  lines+=['### 3. Game script & tendencies',json.dumps(g['context'])]
  for t,c in g['teams'].items():lines+=[f"- {t}: recent RZ pass rate {c['rzPassRate']}, RZ pass-over-expected {c['rzPassOverExpectedPercentagePoints']} percentage points, neutral seconds/play {c['neutralSecondsPerPlay']}. {c['scenario']}"]
  lines+=['### 4. Value selections · research only unless all gates pass']
  for p in g['candidates']:
   q=p['quotes'][0] if p['quotes'] else None;lines+=[f"- **{p['name']} — {p['risk']}**: estimated ATTD {p['probability']:.1%}; fair odds {p['fairOdds']}; opponent allows {p['opponentPositionTDPerGame']:.2f} direct TDs/game to the position group. "+(f"{q['book']} {q['price']}; estimated return {q['estimatedReturn']:.1%}; flags: {', '.join(q['flags']) or 'all gates passed'}." if q else 'No matched ATTD sportsbook price; no price-based value claim.')]
 lines+=['','## Methodology & limitations',*['- '+s for s in report['methodology']]];path.write_text('\n'.join(lines)+'\n')
if __name__=='__main__':report()
