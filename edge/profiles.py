"""Public basic-stat profiles and actual game histories. No estimated box scores."""
import numpy as np
import pandas as pd
COUNTERS=['completions','attempts','passing_yards','passing_tds','passing_interceptions','sacks_suffered',
 'sack_yards_lost','sack_fumbles','sack_fumbles_lost','passing_air_yards','passing_yards_after_catch',
 'passing_first_downs','passing_2pt_conversions','carries','rushing_yards','rushing_tds','rushing_fumbles',
 'rushing_fumbles_lost','rushing_first_downs','rushing_2pt_conversions','targets','receptions','receiving_yards',
 'receiving_tds','receiving_fumbles','receiving_fumbles_lost','receiving_air_yards','receiving_yards_after_catch',
 'receiving_first_downs','receiving_2pt_conversions']

def aggregate(games):
    totals={k:float(pd.to_numeric(games[k],errors='coerce').sum(min_count=1)) if k in games else np.nan for k in COUNTERS}
    def ratio(a,b,factor=1):
        return totals[a]/totals[b]*factor if np.isfinite(totals.get(b,np.nan)) and totals[b]>0 else np.nan
    totals.update({'recorded_games':len(games),'completion_pct':ratio('completions','attempts',100),
        'yards_per_attempt':ratio('passing_yards','attempts'),'yards_per_carry':ratio('rushing_yards','carries'),
        'catch_pct':ratio('receptions','targets',100),'yards_per_reception':ratio('receiving_yards','receptions'),
        'adot':ratio('receiving_air_yards','targets'),'yac_per_reception':ratio('receiving_yards_after_catch','receptions')})
    if totals['attempts']>0 and all(np.isfinite(totals[k]) for k in ['completions','passing_yards','passing_tds','passing_interceptions']):
        a=totals['attempts']
        parts=[(totals['completions']/a-.3)*5,(totals['passing_yards']/a-3)*.25,totals['passing_tds']/a*20,2.375-totals['passing_interceptions']/a*25]
        totals['passer_rating']=sum(np.clip(v,0,2.375) for v in parts)/6*100
    else:totals['passer_rating']=np.nan
    totals['scrimmage_yards']=totals['rushing_yards']+totals['receiving_yards']
    totals['total_touchdowns']=totals['rushing_tds']+totals['receiving_tds']
    return totals

def player_profiles(stats,schedules,season):
    d=stats.drop(columns=['game_id','opponent_team'],errors='ignore').merge(schedules,on=['season','week','team'],validate='many_to_one')
    d=d[d.completed & d.season.eq(season)].copy()
    profiles=[]
    for pid,g in d.sort_values('kickoff').groupby('player_id',sort=False):
        last=g.iloc[-1]
        history=[]
        for r in g.to_dict('records'):
            item={k:r.get(k,np.nan) for k in COUNTERS}
            item.update({'season':int(r['season']),'week':int(r['week']),'gameId':r['game_id'],
                         'opponent':r['opponent_team'],'team':r['team'],'kickoff':r['kickoff'].isoformat()})
            history.append(item)
        total=aggregate(g)
        pergame={k:(v/len(g) if k in COUNTERS+['scrimmage_yards','total_touchdowns'] else v) for k,v in total.items()}
        profiles.append({'playerId':pid,'name':last.player_display_name,'position':last.position,'team':last.team,
                         'season':season,'recordedGames':len(g),'basicStats':{'season':total,'perGame':pergame,
                         'last5':aggregate(g.tail(5)),'lastGame':aggregate(g.tail(1))},'history':history,
                         'statsScope':'Regular-season games with a published stat or mapped offensive-snap row; DNPs are not zero-filled.'})
    return profiles
