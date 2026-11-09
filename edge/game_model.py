"""Separate, chronological NFL score-distribution model. No sportsbook lines enter predictors."""
import datetime as dt
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
from .data import schedule_rows,team
from .model import DistributionForest
ROOT=Path(__file__).resolve().parents[1]
TEAM_METRICS=['passing_epa','rushing_epa','attempts','carries','sacks_suffered','completions','passing_yards','rushing_yards']

def build_rows(schedule,team_stats,now=None):
    now=pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    s=schedule_rows(schedule);s=s[s.home.eq(1)].sort_values('kickoff').copy();raw=schedule.set_index('game_id');lookup={}
    if not team_stats.empty:
        for r in team_stats.to_dict('records'):lookup[(int(r['season']),int(r['week']),team(r['team']))]=r
    history={};league=[];rows=[]
    for game in s.itertuples():
        record=raw.loc[game.game_id];home=game.home_team;away=game.away_team;h=history.get(home,[]);a=history.get(away,[])
        if len(h)>=3 and len(a)>=3:
            row={'game_id':game.game_id,'season':int(game.season),'week':int(game.week),'kickoff':game.kickoff,'home_team':home,'away_team':away,'forecast':bool(not game.completed and game.kickoff>now),'completed':bool(game.completed and game.kickoff<now)}
            for role,games in [('home',h),('away',a)]:
                prior=[g for g in games if g['kickoff']<game.kickoff]
                row[role+'_rest']=min(120,(game.kickoff-prior[-1]['kickoff']).total_seconds()/86400)
                for window in [3,5,8]:
                    last=prior[-window:]
                    for key in ['points_for','points_against',*TEAM_METRICS]:row[role+'_'+key+'_last'+str(window)]=float(np.nanmean([g.get(key,np.nan) for g in last])) if any(pd.notna(g.get(key)) for g in last) else np.nan
                for key in ['passing_epa_allowed','rushing_epa_allowed']:
                    last=prior[-8:];row[role+'_'+key+'_last8']=float(np.nanmean([g.get(key,np.nan) for g in last])) if any(pd.notna(g.get(key)) for g in last) else np.nan
            advantage=float(np.mean([x[0]-x[1] for x in league[-128:]])/2) if league else 1.
            row['baseline_home']=(row['home_points_for_last8']+row['away_points_against_last8'])/2+advantage
            row['baseline_away']=(row['away_points_for_last8']+row['home_points_against_last8'])/2-advantage
            row['home_points']=float(record.home_score) if row['completed'] else np.nan;row['away_points']=float(record.away_score) if row['completed'] else np.nan;rows.append(row)
        if game.completed and game.kickoff<now:
            hp=float(record.home_score);ap=float(record.away_score);hs=lookup.get((game.season,game.week,home),{});ats=lookup.get((game.season,game.week,away),{})
            for club,scored,allowed,own,opponent in [(home,hp,ap,hs,ats),(away,ap,hp,ats,hs)]:history.setdefault(club,[]).append({'kickoff':game.kickoff,'points_for':scored,'points_against':allowed,**{k:own.get(k,np.nan) for k in TEAM_METRICS},'passing_epa_allowed':opponent.get('passing_epa',np.nan),'rushing_epa_allowed':opponent.get('rushing_epa',np.nan)})
            league.append((hp,ap))
    d=pd.DataFrame(rows);metadata={'game_id','season','week','kickoff','home_team','away_team','forecast','completed','home_points','away_points'};features=[c for c in d if c not in metadata]
    return d,features

def metrics(samples,rows,training):
    home=samples[:,:,0];away=samples[:,:,1];margin=home-away;total=home+away;actual_margin=(rows.home_points-rows.away_points).to_numpy();actual_total=(rows.home_points+rows.away_points).to_numpy();base_margin=(rows.baseline_home-rows.baseline_away).to_numpy();base_total=(rows.baseline_home+rows.baseline_away).to_numpy();ph=(margin>0).mean(axis=1)
    residual=(training.home_points-training.away_points-training.baseline_home+training.baseline_away).to_numpy();pb=np.asarray([(residual+x>0).mean() for x in base_margin]);outcome=(actual_margin>0).astype(float)
    result={'n':len(rows),'homeWinBrier':float(np.mean((ph-outcome)**2)),'baselineHomeWinBrier':float(np.mean((pb-outcome)**2)),'homeWinLogLoss':float(np.mean(-(outcome*np.log(np.clip(ph,1e-6,1-1e-6))+(1-outcome)*np.log(np.clip(1-ph,1e-6,1-1e-6))))),'calibration':[]}
    for key,draws,actual,baseline in [('spread',margin,actual_margin,base_margin),('total',total,actual_total,base_total)]:
        low,high=np.quantile(draws,[.1,.9],axis=1);mean=draws.mean(axis=1);result[key]={'mae':float(np.mean(np.abs(mean-actual))),'baselineMae':float(np.mean(np.abs(baseline-actual))),'rmse':float(np.sqrt(np.mean((mean-actual)**2))),'coverage80':float(np.mean((actual>=low)&(actual<=high)))}
    for lo in np.arange(0,1,.1):
        mask=(ph>=lo)&(ph<lo+.1 if lo<.9 else ph<=1)
        if mask.any():result['calibration'].append({'n':int(mask.sum()),'predicted':float(ph[mask].mean()),'observed':float(outcome[mask].mean())})
    return result

def fair(win,push):
    if not 0<win<1-push:return None
    p=win/(1-push);return round(-100*p/(1-p)) if p>=.5 else round(100*(1-p)/p)

def run(out=ROOT/'data',trees=96):
    os.environ.setdefault('NFLREADPY_CACHE','filesystem');os.environ.setdefault('NFLREADPY_CACHE_DIR',str(ROOT/'work/nflreadpy-cache'))
    import nflreadpy as nfl
    now=pd.Timestamp.now(tz='UTC');season=now.year if now.month>=3 else now.year-1;seasons=list(range(2021,season+1));schedule=nfl.load_schedules(seasons).to_pandas();team_stats=nfl.load_team_stats(seasons).to_pandas();frame,features=build_rows(schedule,team_stats,now);past=frame[frame.completed].dropna(subset=['home_points','away_points']);folds=[];all_draws=[];all_rows=[];last_train=None
    for week in sorted(past.loc[past.season.eq(season),'week'].unique()):
        train=past[(past.season<season)|((past.season==season)&(past.week<week))];test=past[past.season.eq(season)&past.week.eq(week)]
        if len(train)<500 or test.empty:continue
        model=DistributionForest(trees=trees,min_leaf=20).fit(train[features],train[['home_points','away_points']]);draws=model.sample(test[features],draws=1024);m=metrics(draws,test,train);folds.append({'week':int(week),'trainingGames':len(train),'testGames':len(test),'metrics':m});all_draws.append(draws);all_rows.append(test);last_train=train
    if not all_draws:raise ValueError('Insufficient chronological game tests')
    aggregate=metrics(np.concatenate(all_draws),pd.concat(all_rows),last_train)
    # The aggregate baseline probability residual distribution must be fitted before each fold.
    aggregate['baselineHomeWinBrier']=sum(f['metrics']['baselineHomeWinBrier']*f['testGames'] for f in folds)/aggregate['n']
    aggregate['calibrationScope']='Home-win probabilities; ties are not wins. Reconstructed final-corrected public games, not archived sportsbook wagers.'
    gates={'moneyline':bool(aggregate['n']>=100 and aggregate['homeWinBrier']<aggregate['baselineHomeWinBrier']),**{k:bool(aggregate['n']>=100 and aggregate[k]['mae']<aggregate[k]['baselineMae'] and .7<=aggregate[k]['coverage80']<=.95) for k in ['spread','total']}}
    future=frame[frame.forecast & (frame.kickoff<=now+pd.Timedelta(days=8))];model=DistributionForest(trees=trees,min_leaf=20).fit(past[features],past[['home_points','away_points']]);draws=model.sample(future[features],draws=10000) if len(future) else np.zeros((0,10000,2));predictions=[]
    for i,row in enumerate(future.itertuples()):
        pairs=draws[i].astype(int);h=pairs[:,0];a=pairs[:,1];p_home=float(np.mean(h>a));p_away=float(np.mean(a>h));p_tie=float(np.mean(h==a));predictions.append({'gameId':row.game_id,'homeTeam':row.home_team,'awayTeam':row.away_team,'kickoff':row.kickoff.isoformat(),'homePoints':float(h.mean()),'awayPoints':float(a.mean()),'total':float((h+a).mean()),'homeSpread':float((a-h).mean()),'awaySpread':float((h-a).mean()),'probHomeWin':p_home,'probAwayWin':p_away,'probTie':p_tie,'homeMoneylineFair':fair(p_home,p_tie),'awayMoneylineFair':fair(p_away,p_tie),'samples':pairs.tolist(),'homePointsInterval80':np.quantile(h,[.1,.9]).tolist(),'awayPointsInterval80':np.quantile(a,[.1,.9]).tolist(),'totalInterval80':np.quantile(h+a,[.1,.9]).tolist(),'marginInterval80':np.quantile(h-a,[.1,.9]).tolist()})
    complete=frame[frame.season.eq(season)].groupby('week').completed.all();complete_weeks=set(complete[complete].index);holdouts=[f for f in folds if f['week'] in complete_weeks]
    payload={'generatedAt':now.isoformat(),'season':season,'model':'Joint home/away score conditional-outcome forest v1','status':'Research game projections; not a validated betting-return model','trainingGames':len(past),'drawsPerGame':10000,'featureNames':features,'validation':{'aggregate':aggregate,'folds':folds,'latestCompleteWeekHoldout':holdouts[-1]['week'] if holdouts else None,'partialWeeks':[f['week'] for f in folds if f['week'] not in complete_weeks]},'validationGates':gates,'projections':predictions,'limitations':['No sportsbook spreads, totals or moneylines enter the predictors.','Joint observed home/away score pairs preserve empirical margin/total dependence.','Current roster, injury and weather impacts are not independently calibrated in this game model.','Fair two-way moneylines condition on no tie; settlement rules require review.','70% estimated win probability does not establish a realized 70% win rate or profitability.','No historical odds ROI or CLV is claimed.']}
    from .game_history import merge_history
    try:history=json.loads((out/'game-projection-history.json').read_text())
    except (OSError,ValueError):history={}
    try:previous=json.loads((out/'game-projections.json').read_text())
    except (OSError,ValueError):previous={}
    history=merge_history(merge_history(history,previous),payload)
    out.mkdir(parents=True,exist_ok=True)
    (out/'game-projection-history.json').write_text(json.dumps(history,separators=(',',':'),allow_nan=False))
    out.mkdir(parents=True,exist_ok=True);(out/'game-projections.json').write_text(json.dumps(payload,separators=(',',':'),allow_nan=False));print(json.dumps({'games':len(predictions),'drawsPerGame':10000,'metrics':aggregate,'validationGates':gates,'holdout':payload['validation']['latestCompleteWeekHoldout']},indent=2));return payload
if __name__=='__main__':run()
