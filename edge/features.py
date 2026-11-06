"""Features use only earlier games, never the target game's outcomes."""
import numpy as np
import pandas as pd

KEYS=['player_id','season','week','team']
METRICS=['targets','receptions','receiving_yards','receiving_air_yards','receiving_yards_after_catch','offense_snaps','offense_pct','receiving_tds','receiving_first_downs','carries','rushing_yards','rushing_tds','rushing_first_downs','attempts','completions','passing_yards','passing_tds','passing_interceptions','passing_first_downs','sack_fumbles','rushing_fumbles','receiving_fumbles','sacks_suffered','passing_air_yards','passing_epa','passing_cpoe','rushing_epa','receiving_epa']

def prepare(stats,schedules,now=None):
    now=pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    if stats.duplicated(KEYS).any():
        raise ValueError('Duplicate player-game rows')
    d=stats.drop(columns=['game_id','opponent_team'],errors='ignore').merge(schedules,on=['season','week','team'],how='inner',validate='many_to_one')
    d=d[d.completed & (d.kickoff<now)].copy()
    d['forecast']=False
    current_season=int(schedules.season.max())
    future=schedules[(schedules.kickoff>now)&(schedules.kickoff<=now+pd.Timedelta(days=8))].copy()
    future=future.sort_values('kickoff').drop_duplicates('team')
    recent=d[d.season.eq(current_season)].sort_values('kickoff').groupby('player_id').tail(1)
    recent=recent[recent.kickoff>=now-pd.Timedelta(days=35)]
    f=recent[['player_id','player_display_name','position','team']].merge(future,on='team')
    f['forecast']=True
    for key in METRICS:
        f[key]=np.nan
    d=pd.concat([d,f],ignore_index=True).sort_values(['kickoff','game_id','player_id'])
    features=['home','week']
    d['position_code']=d.position.map({'WR':0,'TE':1,'RB':2,'QB':3})
    features.append('position_code')
    grouped=d.groupby('player_id',sort=False)
    d['prior_games']=grouped.cumcount()
    features.append('prior_games')
    previous=grouped.kickoff.shift(1)
    d['days_since_game']=(d.kickoff-previous).dt.total_seconds()/86400
    d['changed_team']=(d.team!=grouped.team.shift(1)).astype(float)
    features+=['days_since_game','changed_team']
    lagged={}
    for key in METRICS:
        if key not in d:
            d[key]=np.nan
        for window in [3,6,12]:
            name=f'{key}_last{window}'
            lagged[name]=d.groupby('player_id',sort=False)[key].transform(lambda s:s.shift(1).rolling(window,min_periods=1).mean())
            features.append(name)
    d=pd.concat([d,pd.DataFrame(lagged,index=d.index)],axis=1).copy()
    d['adot_last6']=d.receiving_air_yards_last6/d.targets_last6.replace(0,np.nan)
    d['yac_per_catch_last6']=d.receiving_yards_after_catch_last6/d.receptions_last6.replace(0,np.nan)
    d['catch_rate_last6']=d.receptions_last6/d.targets_last6.replace(0,np.nan)
    d['usage_trend']=d.targets_last3-d.targets_last12
    d['snap_trend']=d.offense_pct_last3-d.offense_pct_last12
    features+=['adot_last6','yac_per_catch_last6','catch_rate_last6','usage_trend','snap_trend']
    # Use one row per team/game. Final current-game totals are shifted before joining.
    actual=d[~d.forecast]
    context_metrics=['targets','receiving_yards','carries','rushing_yards','attempts','passing_yards','sacks_suffered']
    totals=actual.groupby(['game_id','season','week','team','opponent_team','kickoff'],as_index=False)[context_metrics].sum(min_count=1)
    team_context=pd.concat([totals,future[['game_id','season','week','team','opponent_team','kickoff']]],ignore_index=True).drop_duplicates(['game_id','team']).sort_values('kickoff')
    for key in context_metrics:
        name='team_'+key+'_last6'
        team_context[name]=team_context.groupby('team')[key].transform(lambda s:s.shift(1).rolling(6,min_periods=1).mean())
        d=d.merge(team_context[['game_id','team',name]],on=['game_id','team'],how='left',validate='many_to_one')
        features.append(name)
        # opponent's receiving yards/targets allowed in completed earlier games only
        defense=totals.rename(columns={'team':'offense','opponent_team':'team'})
        pieces=[]
        for row in d[['game_id','opponent_team','kickoff']].drop_duplicates().itertuples():
            history=defense[(defense.team==row.opponent_team)&(defense.kickoff<row.kickoff)].sort_values('kickoff').tail(6)
            pieces.append({'game_id':row.game_id,'opponent_team':row.opponent_team,'opp_allowed_'+key+'_last6':history[key].mean()})
        name='opp_allowed_'+key+'_last6'
        d=d.merge(pd.DataFrame(pieces),on=['game_id','opponent_team'],how='left',validate='many_to_one')
        features.append(name)
    d['target_share_last6']=d.targets_last6/d.team_targets_last6.replace(0,np.nan)
    features.append('target_share_last6')
    for name,numerator,denominator in [('carry_share','carries_last6','team_carries_last6'),('completion_rate','completions_last6','attempts_last6'),('pass_ypa','passing_yards_last6','attempts_last6'),('rush_ypc','rushing_yards_last6','carries_last6'),('sack_rate','sacks_suffered_last6','attempts_last6')]:
        d[name]=d[numerator]/d[denominator].replace(0,np.nan)
        features.append(name)
    return d.sort_values(['season','week','kickoff','player_id']).reset_index(drop=True),features
