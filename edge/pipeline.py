"""python -m edge.pipeline --season 2026 --start-season 2021"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .data import collect
from .features import prepare
from .model import DistributionForest, TARGETS, walk_forward
from .routes import scenario

def clean(value):
    if isinstance(value,dict): return {k:clean(v) for k,v in value.items()}
    if isinstance(value,list): return [clean(v) for v in value]
    if isinstance(value,(float,np.floating)) and not np.isfinite(value): return None
    if isinstance(value,np.generic): return value.item()
    return value

def run(start,season,out,trees=96):
    now=pd.Timestamp.now(tz='UTC')
    stats,schedules,sumer,sources,quality=collect(start,season,out/'snapshots')
    schedules=schedules[schedules.season.between(start,season)]
    frame,features=prepare(stats,schedules,now)
    quality['latestObservedStatsWeekBySeason']={str(int(k)):int(v) for k,v in frame[~frame.forecast].groupby('season').week.max().items()}
    published=set(frame[~frame.forecast].game_id.unique())
    completed=set(schedules[schedules.completed & (schedules.kickoff<now)].game_id.unique())
    quality['completedScheduleGamesWithoutPlayerRows']=sorted(completed-published)
    season_games=schedules[schedules.season.eq(season)]
    season_games=season_games.copy()
    season_games['publishedComplete']=season_games.completed & season_games.game_id.isin(published)
    complete_weeks=set(season_games.groupby('week').publishedComplete.all().loc[lambda s:s].index.astype(int))
    validation=walk_forward(frame,features,season,trees=trees,complete_weeks=complete_weeks)
    history=frame[(~frame.forecast)&(frame.prior_games>=3)].dropna(subset=TARGETS)
    forecast=frame[frame.forecast & frame.prior_games.ge(3)]
    if len(history)<500:
        raise ValueError('Insufficient history')
    model=DistributionForest(trees=trees).fit(history[features],history[TARGETS])
    draws=model.sample(forecast[features]) if len(forecast) else np.empty((0,512,2))
    rows=[]
    for j,player in enumerate(forecast.itertuples()):
        rows.append({'playerId':player.player_id,'name':player.player_display_name,'position':player.position,
                     'team':player.team,'opponent':player.opponent_team,'homeTeam':player.home_team,'awayTeam':player.away_team,
                     'gameId':player.game_id,'kickoff':player.kickoff.isoformat(), 'availabilityConfirmed':False,
                     'historyGames':int(player.prior_games),'daysSinceGame':float(player.days_since_game),
                     'features':{key:float(getattr(player,key)) for key in features},
                     'samples':draws[j].astype(int).tolist(),
                     'routeScenario':scenario(player,frame,sumer,season,now)})
    gates={key:bool(m['n']>=500 and m['mae']<m['rollingBaselineMae'] and .7<=m['coverage80']<=.95)
           for key,m in validation['aggregate'].items()}
    gates['currentSeasonGameCoverage']=not any(g.startswith(str(season)+'_') for g in quality['completedScheduleGamesWithoutPlayerRows'])
    bundle={'schemaVersion':2,'generatedAt':now.isoformat(),'season':season,'model':'Conditional outcome forest v0.2',
            'status':'research; no historical sportsbook-price backtest',
            'validationPassed':all(gates.values()),'validationGates':gates,'validation':validation,
            'dataQuality':quality,'sources':sources,'featureNames':features,'forecasts':rows,
            'limitations':['Historical feeds contain final stat corrections, not archived pregame vintages.',
                          'Current route scenario is heuristic and excluded from historical validation.',
                          'Injuries, trades after last appearance, availability, weather and live game state require review.',
                          'No guaranteed edge; no ROI or CLV established without point-in-time sportsbook odds.',
                          'Forecasts are conditional on active participation; DNP/void rules differ by book.'],
            'sumerStatus':{k:{field:v for field,v in value.items() if field!='players'} for k,value in sumer.items()}}
    out.mkdir(parents=True,exist_ok=True)
    bundle=clean(bundle)
    temporary=out/'latest.json.tmp'
    temporary.write_text(json.dumps(bundle,separators=(',',':'),allow_nan=False),encoding='utf-8')
    temporary.replace(out/'latest.json')
    report={k:v for k,v in validation.items() if k!='predictions'}
    (out/'validation.json').write_text(json.dumps(clean(report),indent=2,allow_nan=False))
    (out/'oos-predictions.json').write_text(json.dumps(clean(validation['predictions']),indent=2))
    return {'forecasts':len(rows),'testedWeeks':len(validation['folds']),'validationGates':gates,'latestWeekHoldout':validation['latestWeekHoldout']['week']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--season',required=True,type=int)
    p.add_argument('--start-season',default=2021,type=int)
    p.add_argument('--output',type=Path,default=Path('data'))
    p.add_argument('--trees',type=int,default=96)
    args=p.parse_args()
    if args.start_season>=args.season:
        p.error('Use at least one earlier training season')
    print(json.dumps(run(args.start_season,args.season,args.output,args.trees),indent=2))
