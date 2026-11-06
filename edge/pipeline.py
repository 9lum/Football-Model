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

def run(start,season,out,trees=96,as_of=None,enrich=True):
    now=pd.Timestamp.now(tz='UTC') if as_of is None else pd.Timestamp(as_of)
    stats,schedules,sumer,sources,quality=collect(start,season,out/'snapshots')
    schedules=schedules[schedules.season.between(start,season)]
    current_teams={};current_positions={};trade_notes={};depth=[];enrichment={};defense_games=pd.DataFrame();receiver_priors=pd.DataFrame();coverage={}
    if enrich:
        from .advanced import attach as attach_ngs
        stats,ngs_sources=attach_ngs(stats,start,season)
        enrichment['nextGenStats']=ngs_sources
        from .availability import latest_depth,public_csv
        from .context import current_team_map,collect_defense,parse_coverage
        from .data import get
        import io
        try:
            depth=latest_depth(public_csv('depth_charts',f'depth_charts_{season}.csv.gz',Path('work/reference-cache')),now)
            current_positions={r['playerId']:r['position'] for r in depth if r['fresh']}
            people=public_csv('players','players.csv.gz',Path('work/reference-cache'))
            raw,_=get('https://raw.githubusercontent.com/nflverse/nfldata/master/data/trades.csv')
            current_teams,trade_notes=current_team_map(depth,pd.read_csv(io.BytesIO(raw)),people,now)
            enrichment['roster']='current public depth chart and trade ledger'
        except Exception as e:enrichment['rosterError']=type(e).__name__
        defense_games,receiver_priors,defense_sources=collect_defense(start,season,Path('work/defense-cache'))
        enrichment['defenseSources']=defense_sources
        enrichment['coverageBacktestScope']='Prior-season charted coverage only; fresh aggregate coverage is applied only to upcoming games.'
        try:
            raw,_=get('https://www.sharpfootballanalysis.com/stats-nfl/nfl-coverage-schemes/')
            coverage=parse_coverage(raw.decode(),now)
        except Exception as e:enrichment['currentCoverageError']=type(e).__name__
    frame,features=prepare(stats,schedules,now,current_teams,current_positions)
    if not defense_games.empty:
        from .context import attach_defense
        frame,features=attach_defense(frame,features,defense_games,receiver_priors,schedules,coverage)
    quality['latestObservedStatsWeekBySeason']={str(int(k)):int(v) for k,v in frame[~frame.forecast].groupby('season').week.max().items()}
    published=set(frame[~frame.forecast].game_id.unique())
    completed=set(schedules[schedules.completed & (schedules.kickoff<now)].game_id.unique())
    quality['completedScheduleGamesWithoutPlayerRows']=sorted(completed-published)
    season_games=schedules[schedules.season.eq(season)]
    season_games=season_games.copy()
    season_games['publishedComplete']=season_games.completed & season_games.game_id.isin(published)
    complete_weeks=set(season_games.groupby('week').publishedComplete.all().loc[lambda s:s].index.astype(int))
    from .config import FAMILIES, MARKET_SPECS
    from .profiles import player_profiles
    profiles=player_profiles(stats,schedules,season)
    for profile in profiles:
        if profile['playerId'] in current_teams:
            profile['statHistoryTeam']=profile['team'];profile['team']=current_teams[profile['playerId']]
        if profile['playerId'] in current_positions:profile['position']=current_positions[profile['playerId']]
        if profile['playerId'] in trade_notes:profile['trade']=trade_notes[profile['playerId']]
    profile_lookup={p['playerId']:p for p in profiles}
    forecast=frame[frame.forecast & frame.prior_games.ge(3)]
    rows={}
    for player in forecast.itertuples():
        profile=profile_lookup.get(player.player_id,{})
        rows[player.player_id]={'playerId':player.player_id,'name':player.player_display_name,'position':player.position,
            'team':player.team,'opponent':player.opponent_team,'homeTeam':player.home_team,'awayTeam':player.away_team,
            'gameId':player.game_id,'kickoff':player.kickoff.isoformat(),'availabilityConfirmed':False,
            'historyGames':int(player.prior_games),'daysSinceGame':float(player.days_since_game),
            'features':{key:float(getattr(player,key)) for key in features},'marketSamples':{},
            'routeScenario':scenario(player,frame,sumer,season,now) if player.position in ['WR','TE','RB'] else {'status':'not_applicable'}}
    validations={}; market_gates={}; family_features={}; failures={}
    coverage_ok=not any(g.startswith(str(season)+'_') for g in quality['completedScheduleGamesWithoutPlayerRows'])
    for family,spec in FAMILIES.items():
        targets=spec['targets']
        patterns={'receiving':['target','recept','receiv','adot','yac','catch','usage','team_attempts','opp_allowed_passing_yards'],
                  'rushing':['carr','rush','attempts','passing_yards'],
                  'passing':['attempt','complet','passing','sack','pass_ypa','opp_allowed_receiving']}[family]
        common=['home','week','position_code','prior_games','days_since_game','changed_team']
        selected=[key for key in features if key in common or any(v in key for v in patterns+['offense_','snap_','matchup_','coverage_'])]
        family_features[family]=selected
        volume,minimum={'receiving':('targets_last3',1.),'rushing':('carries_last3',2.),'passing':('attempts_last3',10.)}[family]
        family_frame=frame[frame[volume].ge(minimum)]
        eligible=family_frame[(~family_frame.forecast)&(family_frame.prior_games>=3)&family_frame.position.isin(spec['positions'])].dropna(subset=targets)
        if len(eligible)<500:
            failures[family]='Insufficient published outcomes for this model family'
            continue
        selection={'method':'Fixed feature family; no current-season outcome used for feature selection'}
        basic=[k for k in selected if not k.startswith(('matchup_','coverage_'))]
        historical_train=eligible[eligible.season<=season-2];development=eligible[eligible.season.eq(season-1)]
        if selected!=basic and len(historical_train)>=500 and len(development)>=100:
            baseline_errors=np.asarray([np.mean(np.abs(development[key].to_numpy()-development[key+'_last6'].fillna(historical_train[key].median()).to_numpy())) for key in targets])
            target_values=development[targets].to_numpy()
            fit_basic=DistributionForest(trees=trees).fit(historical_train[basic],historical_train[targets])
            fit_defense=DistributionForest(trees=trees).fit(historical_train[selected],historical_train[targets])
            basic_score=float(np.mean(np.mean(np.abs(fit_basic.predict_mean(development[basic])-target_values),axis=0)/np.maximum(baseline_errors,.05)))
            defense_score=float(np.mean(np.mean(np.abs(fit_defense.predict_mean(development[selected])-target_values),axis=0)/np.maximum(baseline_errors,.05)))
            use_defense=defense_score<basic_score*.99
            selection={'method':'Earlier-season development comparison; current-season holdout untouched','developmentSeason':season-1,
                'baselineFeatureScore':basic_score,'defenseFeatureScore':defense_score,'minimumRelativeImprovement':.01,
                'selected':'defensive_context' if use_defense else 'basic_context','developmentRows':len(development)}
            if not use_defense:selected=basic
            del fit_basic,fit_defense
        family_features[family]=selected
        report=walk_forward(family_frame,selected,season,trees=trees,complete_weeks=complete_weeks,targets=targets,positions=spec['positions'])
        report['featureSelection']=selection
        report['cohort']={'positions':spec['positions'],'priorVolumeFeature':volume,'minimum':minimum}
        validations[family]=report
        fitted=DistributionForest(trees=trees).fit(eligible[selected],eligible[targets])
        future=forecast[forecast.position.isin(spec['positions']) & forecast[volume].ge(minimum)]
        draws=fitted.sample(future[selected]) if len(future) else np.empty((0,512,len(targets)))
        for market,(label,group,target) in MARKET_SPECS.items():
            if group!=family: continue
            metric=report['aggregate'][target]
            required_n=200 if family=='passing' else 500
            gate=bool(metric['n']>=required_n and metric['mae']<metric['rollingBaselineMae'] and .7<=metric['coverage80']<=.95 and coverage_ok)
            market_gates[market]=gate
            for j,player in enumerate(future.itertuples()):
                values=draws[j,:,targets.index(target)].astype(int)
                rows[player.player_id]['marketSamples'][market]={'label':label,'target':target,'family':family,
                    'values':values.tolist(),'mean':float(values.mean()),'p10':float(np.quantile(values,.1)),
                    'p90':float(np.quantile(values,.9)),'validationPassed':gate}
    if 'receiving' not in validations:
        raise ValueError('Receiving model could not be evaluated')
    validation=validations['receiving']
    bundle={'schemaVersion':3,'generatedAt':now.isoformat(),'season':season,'model':'Position-specific conditional outcome forests v0.3',
        'status':'research; no historical sportsbook-price backtest','validationPassed':all(market_gates.values()),
        'validationGates':market_gates,'validation':{k:v for k,v in validation.items() if k!='predictions'},'familyValidation':{family:{k:v for k,v in value.items() if k!='predictions'} for family,value in validations.items()},'modelFailures':failures,
        'dataQuality':quality,'enrichment':enrichment,'currentCoverage':coverage,'sources':sources,'featureNames':features,'featureNamesByFamily':family_features,
        'forecasts':[r for r in rows.values() if r['marketSamples']],'players':profiles,
        'marketConfig':{k:{'label':v[0],'family':v[1],'target':v[2],'positions':FAMILIES[v[1]]['positions']} for k,v in MARKET_SPECS.items()},
        'limitations':['Historical feeds contain final stat corrections, not archived pregame vintages.',
            'Current route scenario is heuristic and excluded from historical validation.',
            'Injuries, trades after last appearance, availability, weather and live game state require review.',
            'No guaranteed edge; no ROI or CLV established without point-in-time sportsbook odds.',
            'Forecasts are conditional on active participation; DNP/void rules differ by book.'],
        'sumerStatus':{k:{field:v for field,v in value.items() if field!='players'} for k,value in sumer.items()}}
    out.mkdir(parents=True,exist_ok=True)
    bundle=clean(bundle)
    from .audit import write_audit
    audit=write_audit(out,frame,season,now)
    temporary=out/'latest.json.tmp'
    temporary.write_text(json.dumps(bundle,separators=(',',':'),allow_nan=False),encoding='utf-8')
    temporary.replace(out/'latest.json')
    report={k:v for k,v in validation.items() if k!='predictions'}
    report['families']={family:{k:v for k,v in value.items() if k!='predictions'} for family,value in validations.items()}
    (out/'validation.json').write_text(json.dumps(clean(report),indent=2,allow_nan=False))
    (out/'oos-predictions.json').write_text(json.dumps(clean([dict(item,family=family) for family,report in validations.items() for item in report['predictions']]),indent=2))
    return {'defenseGames':len(defense_games),'coveragePriorRows':len(receiver_priors),'currentCoverageTeams':len(coverage),'rosterOverrides':len(current_teams),'tradeNotes':len(trade_notes),'featureSelections':{k:v.get('featureSelection') for k,v in validations.items()},'audit':audit,'forecasts':len(bundle['forecasts']),'testedWeeks':len(validation['folds']),'validationGates':market_gates,'latestWeekHoldout':validation['latestWeekHoldout']['week']}

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
