"""Position-specific opponent allowances, joined strictly before each kickoff.

Aggregate each offense/position/game, including published zero-opportunity games.
Opponent-adjusted residuals compare an allowance with that offense position's
preceding six games, rather than treating every opposing offense as equally strong.
"""
import numpy as np
import pandas as pd

METRICS=['targets','receptions','receiving_yards','receiving_tds','carries','rushing_yards','rushing_tds','attempts','completions','passing_yards','passing_tds','passing_interceptions']
POSITIONS=['QB','RB','WR','TE']

def attach_position_matchups(frame,features,schedules):
    d=frame.copy();actual=d[~d.forecast].copy()
    for key in METRICS:
        if key not in actual:actual[key]=np.nan
    keys=['game_id','season','team','opponent_team','kickoff']
    published=actual[keys].drop_duplicates()
    grid=published.merge(pd.DataFrame({'position':POSITIONS}),how='cross')
    totals=actual.groupby(keys+['position'],as_index=False)[METRICS].sum(min_count=1)
    games=grid.merge(totals,on=keys+['position'],how='left',indicator=True,validate='one_to_one')
    games.loc[games._merge.eq('left_only'),METRICS]=0.
    games=games.drop(columns='_merge').sort_values('kickoff')
    games['td_points']=6*(games.rushing_tds+games.receiving_tds)
    if 'points_allowed' in schedules:
        games=games.merge(schedules[['game_id','team','points_allowed']].drop_duplicates(),on=['game_id','team'],validate='many_to_one')
    else:games['points_allowed']=np.nan
    metrics=METRICS+['td_points','points_allowed']
    # Offensive strength is known BEFORE the game whose allowance is being measured.
    for metric in METRICS:
        baseline=games.groupby(['team','position'])[metric].transform(lambda s:s.shift(1).rolling(6,min_periods=3).mean())
        games[metric+'_residual']=games[metric]-baseline
    defense={k:g.sort_values('kickoff') for k,g in games.groupby(['opponent_team','position'])}
    league={}
    for position,g in games.groupby('position'):
        g=g.sort_values('kickoff');values=g[metrics].to_numpy(float);mask=np.isfinite(values)
        league[position]=(g.kickoff.astype('int64').to_numpy(),np.vstack([np.zeros(len(metrics)),np.nancumsum(values,axis=0)]),np.vstack([np.zeros(len(metrics)),np.cumsum(mask,axis=0)]))
    rows=[]
    queries=d[['game_id','opponent_team','position','season','kickoff']].drop_duplicates()
    for query in queries.itertuples():
        record={'game_id':query.game_id,'opponent_team':query.opponent_team,'position':query.position}
        history=defense.get((query.opponent_team,query.position))
        if history is None:history=games.iloc[:0]
        history=history[history.kickoff<query.kickoff];last=history.tail(6);recent=history.tail(3);season=history[history.season.eq(query.season)]
        record['opp_position_games_last6']=len(last);record['opp_position_games_season']=len(season)
        prior=np.full(len(metrics),np.nan)
        if query.position in league:
            times,sums,counts=league[query.position];i=np.searchsorted(times,query.kickoff.value,side='left')
            np.divide(sums[i],counts[i],out=prior,where=counts[i]>0)
        for j,metric in enumerate(metrics):
            prefix='opp_position_'+metric
            record[prefix+'_last3']=recent[metric].mean()
            record[prefix+'_last6']=last[metric].mean()
            record[prefix+'_season']=season[metric].mean()
            valid=last[metric].dropna();record[prefix+'_shrunk6']=(valid.sum()+3*prior[j])/(len(valid)+3) if len(valid) and np.isfinite(prior[j]) else np.nan
            if metric in METRICS:record[prefix+'_offense_adjusted_delta6']=last[metric+'_residual'].mean()
        for name,numerator,denominator in [('pass_ypa','passing_yards','attempts'),('completion_rate','completions','attempts'),('rush_ypc','rushing_yards','carries'),('catch_rate','receptions','targets'),('yards_per_target','receiving_yards','targets'),('pass_td_rate','passing_tds','attempts'),('interception_rate','passing_interceptions','attempts'),('rush_td_rate','rushing_tds','carries'),('receiving_td_rate','receiving_tds','targets')]:
            matched=last[[numerator,denominator]].dropna();den=matched[denominator].sum()
            record['opp_position_'+name+'_last6']=matched[numerator].sum()/den if den>0 else np.nan
        rows.append(record)
    context=pd.DataFrame(rows);added=[k for k in context if k.startswith('opp_position_')]
    d=d.merge(context,on=['game_id','opponent_team','position'],how='left',validate='many_to_one')
    return d,features+added
