"""Public team detail statistics; final scores and published stat coverage are kept distinct."""
import datetime as dt
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
from edge.data import schedule_rows,team
ROOT=Path(__file__).resolve().parents[1]
METRICS=['passing_yards','rushing_yards','attempts','completions','carries','passing_tds','rushing_tds','passing_interceptions','sacks_suffered','passing_epa','rushing_epa','passing_first_downs','rushing_first_downs']

def summarize_stats(records):
    totals={};per_game={};counts={}
    for key in METRICS:
        values=[float(r[key]) for r in records if pd.notna(r.get(key))]
        totals[key]=sum(values) if values else None;per_game[key]=float(np.mean(values)) if values else None;counts[key]=len(values)
    rates={}
    for key,num,den in [('completion_percentage','completions','attempts'),('passing_yards_per_attempt','passing_yards','attempts'),('rushing_yards_per_carry','rushing_yards','carries')]:
        valid=[r for r in records if pd.notna(r.get(num)) and pd.notna(r.get(den))];denom=sum(float(r[den]) for r in valid)
        rates[key]=sum(float(r[num]) for r in valid)/denom*(100 if key=='completion_percentage' else 1) if denom else None
    return {'totals':totals,'perGame':per_game,'rates':rates,'coverageByStat':counts}

def build(schedule,stats,catalog,season,now=None):
    now=pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now);s=schedule_rows(schedule);s=s[s.season.eq(season)];raw=schedule.set_index('game_id');d=stats[stats.season.eq(season)&stats.week.gt(0)].copy()
    if 'season_type' in d:d=d[d.season_type.eq('REG')]
    lookup={(int(r['week']),team(r['team'])):r for r in d.to_dict('records')};meta={team(r['team_abbr']):r for r in catalog.to_dict('records')};result=[]
    for club in sorted(s.team.unique()):
        rows=[];offense=[];allowed=[];upcoming=[]
        for g in s[s.team.eq(club)].sort_values('kickoff').itertuples():
            if g.completed and g.kickoff<now:
                game=raw.loc[g.game_id];pf=float(game.home_score if g.home else game.away_score);pa=float(game.away_score if g.home else game.home_score);own=lookup.get((g.week,club));opp=lookup.get((g.week,g.opponent_team))
                if own:offense.append(own)
                if opp:allowed.append(opp)
                rows.append({'gameId':g.game_id,'week':int(g.week),'kickoff':g.kickoff.isoformat(),'opponent':g.opponent_team,'isHome':bool(g.home),'pointsFor':pf,'pointsAgainst':pa,'result':'W' if pf>pa else 'L' if pf<pa else 'T','offense':{k:float(own[k]) if own and pd.notna(own.get(k)) else None for k in METRICS}})
            elif not g.completed and g.kickoff>now:upcoming.append({'game_id':g.game_id,'kickoff':g.kickoff.isoformat(),'week':int(g.week),'home_team':g.home_team,'away_team':g.away_team,'opponent':g.opponent_team,'isHome':bool(g.home)})
        n=len(rows);info=meta.get(club,{});record=lambda games:{'wins':sum(g['result']=='W' for g in games),'losses':sum(g['result']=='L' for g in games),'ties':sum(g['result']=='T' for g in games)}
        result.append({'team':club,'name':info.get('team_name',club),'conference':info.get('team_conf'),'division':info.get('team_division'),'logo':info.get('team_logo_espn'),'gamesPlayed':n,'record':record(rows),'homeRecord':record([r for r in rows if r['isHome']]),'awayRecord':record([r for r in rows if not r['isHome']]),'pointsFor':sum(r['pointsFor'] for r in rows),'pointsAgainst':sum(r['pointsAgainst'] for r in rows),'pointsPerGame':float(np.mean([r['pointsFor'] for r in rows])) if n else None,'allowedPerGame':float(np.mean([r['pointsAgainst'] for r in rows])) if n else None,'pointDifferential':sum(r['pointsFor']-r['pointsAgainst'] for r in rows),'offense':summarize_stats(offense),'defenseAllowed':summarize_stats(allowed),'statsGames':len(offense),'games':rows,'upcoming':upcoming})
    for key,ascending in [('pointsPerGame',False),('allowedPerGame',True)]:
        ranking=sorted([r for r in result if r[key] is not None],key=lambda r:r[key],reverse=not ascending)
        for row in result:row[key+'Rank']=next((i+1 for i,r in enumerate(ranking) if r['team']==row['team']),None)
    return result

def run():
    os.environ.setdefault('NFLREADPY_CACHE','filesystem');os.environ.setdefault('NFLREADPY_CACHE_DIR',str(ROOT/'work/nflreadpy-cache'))
    import nflreadpy as nfl
    now=pd.Timestamp.now(tz='UTC');season=now.year if now.month>=3 else now.year-1;rows=build(nfl.load_schedules(season).to_pandas(),nfl.load_team_stats(season).to_pandas(),nfl.load_teams().to_pandas(),season,now);payload={'generatedAt':now.isoformat(),'season':season,'source':'nflreadpy / nflverse schedules, teams and weekly team statistics','teams':rows,'limitations':['Regular-season completed games only. Final-corrected public files may update after games.','Score/result coverage and published stat coverage can differ. Null statistics are not replaced with zero.','Points per game ranks are descriptive current-season rankings, not opponent-adjusted model ratings.']};path=ROOT/'data/team-research.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(payload,separators=(',',':'),allow_nan=False));print(json.dumps({'teams':len(rows),'season':season,'scoredTeamGames':sum(r['gamesPlayed'] for r in rows),'statTeamGames':sum(r['statsGames'] for r in rows)}));return payload
if __name__=='__main__':run()
