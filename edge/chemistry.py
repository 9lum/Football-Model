"""Recency-shrunk, starter-linked receiving splits. Observational research, not causal lift."""
import numpy as np
import pandas as pd
from .data import team

METRICS=['targets','receptions','receiving_yards','receiving_tds']
def starter_games(games,stats,now):
    rows=[]
    for g in games.to_dict('records'):
        if g.get('game_type','REG')!='REG':continue
        stamp=pd.to_datetime(g.get('gameday'),utc=True,errors='coerce')
        if pd.isna(stamp) or stamp>=now.normalize():continue
        for side in ['home','away']:
            if pd.isna(g.get(side+'_score')):continue
            rows.append({'season':g['season'],'week':g['week'],'team':team(g[side+'_team']),'qbId':g.get(side+'_qb_id'),'kickoff':stamp})
    if not rows:return pd.DataFrame()
    d=pd.DataFrame(rows).drop_duplicates(['season','week','team'])
    q=stats[stats.position.eq('QB')].copy()
    totals=q.groupby(['season','week','team']).attempts.sum().rename('teamAttempts').reset_index()
    q=q.rename(columns={'player_id':'qbId','attempts':'qbAttempts'})
    d=d.merge(totals,on=['season','week','team']).merge(q[['season','week','team','qbId','qbAttempts']],on=['season','week','team','qbId'])
    # Do not attribute injury/relief games to a starter who barely played.
    return d[(d.qbAttempts>=15)&(d.qbAttempts>=.8*d.teamAttempts)]

def build_context(stats,games,roles,now):
    now=pd.Timestamp(now);starts=starter_games(games,stats,now)
    if starts.empty:return {'status':'unavailable','players':{}}
    d=stats[stats.position.isin(['WR','TE','RB'])].merge(starts,on=['season','week','team'])
    d=d[d.targets.notna()&d.targets.ge(0)].drop_duplicates(['player_id','season','week','team'])
    d['weight']=np.power(.5,(now-d.kickoff).dt.days/730)
    result={};qbs={r['team']:r for r in roles if r['position']=='QB' and r.get('fresh') and r.get('expectedStarter')}
    def split(g):
        w=g.weight;den=float(w.sum());t=float((g.targets*w).sum());c=float((g.receptions*w).sum())
        return {'games':len(g),'effectiveGames':den,'targets':float(g.targets.sum()),'receivingYardsPerGame':float(g.receiving_yards.mean()),'targetShare':float((g.targets*w).sum()/max(1,(g.teamAttempts*w).sum())),
                'catchRate':float((g.receptions*w).sum()/max(1,t)),'yardsPerCatch':float((g.receiving_yards*w).sum()/max(1,c)),'tdPerTarget':float((g.receiving_tds*w).sum()/max(1,t))}
    for role in roles:
        if role['position'] not in ['WR','TE','RB'] or role['team'] not in qbs:continue
        pid=role['playerId'];g=d[d.player_id.eq(pid)].sort_values('kickoff');qb=qbs[role['team']];pair=g[g.qbId.eq(qb['playerId'])];other=g[~g.qbId.eq(qb['playerId'])]
        if len(pair)<3 or pair.targets.sum()<12 or len(other)<3:continue
        a,b=split(pair),split(other);recent=g.tail(6);recentShare=float(recent.qbId.eq(qb['playerId']).mean());confidence=a['effectiveGames']/(a['effectiveGames']+8)*b['effectiveGames']/(b['effectiveGames']+5)
        def effect(key):return float(np.clip(1+(np.clip(a[key]/max(.01,b[key]),.65,1.35)-1)*confidence*(1-recentShare),.85,1.15))
        targets=effect('targetShare');catches=targets*effect('catchRate');yards=catches*effect('yardsPerCatch');td=catches # Sparse touchdown splits are not fitted independently.
        result[pid]={'qbId':qb['playerId'],'qbName':qb['name'],'team':role['team'],'withQB':a,'otherQBs':b,'recentSameQBShare':recentShare,'confidence':confidence,
          'factors':{'player_targets':targets,'player_receptions':float(np.clip(catches,.85,1.15)),'player_reception_yds':float(np.clip(yards,.85,1.15)),'player_reception_tds':float(np.clip(td,.9,1.1))},
          'status':'Research · QB chemistry','rationale':f"{qb['name']}: {len(pair)} qualifying shared starts versus {len(other)} with other quarterbacks. Recency-weighted opportunity and efficiency splits are shrunk toward no change; recent same-QB usage is removed to avoid counting it twice."}
    return {'status':'available','version':1,'asOf':now.isoformat(),'players':result,'source':'https://github.com/nflverse/nflverse-data/releases/tag/player_stats',
      'method':'Starter-linked weekly statistics; starting QB must supply at least 80% of team attempts and 15 attempts. Two-year recency half-life, eight-game pair and five-game comparison shrinkage; maximum 15% receiving change. Target allocation is conserved within each forecast team. No unsupported same-QB sample means no chemistry adjustment.',
      'limitations':['Starter-linked team-game splits are observational, not exact passer-target charting.','Role, opponent and scheme differences can confound historical splits.','Not yet validated out of sample; adjusted markets cannot pass the betting quality gate.']}
