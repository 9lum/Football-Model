"""Current route-based scenario. Never retroactively inserted into historical folds."""
import re
from urllib.parse import urlparse
import numpy as np
import pandas as pd
from .data import team

def canonical(name):
    return re.sub('[^a-z0-9]','',str(name).lower())

def match_snapshot(player,snapshots,season,now):
    found=[]
    for snapshot in snapshots.values():
        if 'players' not in snapshot:
            continue
        stamp=pd.Timestamp(snapshot['asOf'])
        if stamp>now or stamp<pd.Timestamp(f'{season}-08-01',tz='UTC') or now-stamp>pd.Timedelta(days=7):
            continue
        for row in snapshot['players']:
            # Profile slugs supply full names. No fuzzy/initial-only joins.
            slug=urlparse(row['profileUrl']).path.strip('/').split('/')[-1]
            label_team=row['label'].split()[0]
            if canonical(slug)==canonical(player.player_display_name) and team(label_team)==player.team:
                found.append((row,snapshot))
    return found[0] if len(found)==1 else None

def scenario(player,history,snapshots,season,now,draws=512):
    matched=match_snapshot(player,snapshots,season,now)
    if matched is None:
        return {'status':'unavailable','reason':'No unique, fresh, same-team public route snapshot'}
    route,source=matched
    history=history[(history.player_id==player.player_id)&(history.season==season)&(~history.forecast)]
    targets=float(history.targets.sum());recs=float(history.receptions.sum());yards=float(history.receiving_yards.sum())
    # Route and box-score snapshots must cover the same player results.
    if abs(recs-route['Receptions'])>.01 or abs(yards-route.get('Rec. Yards',yards))>.01:
        return {'status':'unavailable','reason':'Route and nflverse snapshots cover different results'}
    routes=route['Routes Run']
    if not routes or targets<=0 or not len(history):
        return {'status':'unavailable','reason':'Insufficient observed route usage'}
    tprr=targets/routes
    if not 0<=tprr<=1 or abs(tprr-route['Targets/Route Run'])>.025:
        return {'status':'unavailable','reason':'Route/target definitions or snapshot totals disagree'}
    snaps=pd.to_numeric(history.offense_pct,errors='coerce')
    season_share=float(snaps.mean())
    recent_share=float(snaps.tail(3).mean())
    role_change=np.clip(recent_share/season_share,.6,1.5) if season_share>0 else 1.
    routes_projected=routes/len(history)*role_change
    mean_targets=routes_projected*tprr
    dispersion=max(float(history.targets.var(ddof=0))-float(history.targets.mean()),.1)
    shape=max(mean_targets**2/dispersion,.5)
    rng=np.random.default_rng(83)
    tg=rng.poisson(rng.gamma(shape,mean_targets/shape,size=draws))
    cp=(recs+20*.65)/(targets+20)
    catches=rng.binomial(tg,np.clip(cp,0,1))
    # Estimate completion depth separately from target aDOT, instead of treating them as identical.
    recent=history.tail(6)
    observed_adot=recent.receiving_air_yards.sum(min_count=1)/recent.targets.sum() if recent.targets.sum()>0 else np.nan
    completed_air=(recent.receiving_yards.sum()-recent.receiving_yards_after_catch.sum(min_count=1))/max(recent.receptions.sum(),1)
    if not np.isfinite(observed_adot) or not np.isfinite(completed_air) or observed_adot<=0:
        return {'status':'unavailable','reason':'Completed-depth estimate unavailable'}
    depth_ratio=np.clip(completed_air/observed_adot,.25,2.)
    depth=float(route['ADoT'])*depth_ratio
    yac=float(route['YAC'])/max(recs,1)
    per_catch_sd=max(6,abs(float(route['ADoT']))*.85)
    yard_samples=np.rint(catches*(depth+yac)+np.sqrt(catches)*rng.normal(0,per_catch_sd,draws))
    return {'status':'research_scenario','source':source['source'],'asOf':source['asOf'],
            'routes':routes,'targetsPerRoute':tprr,'routesPerTarget':routes/targets,
            'adot':route['ADoT'],'projectedRoutes':float(routes_projected),'projectedTargets':float(mean_targets),
            'note':'Heuristic scenario; current route aggregates have no historical out-of-time validation.',
            'samples':np.column_stack([yard_samples,catches]).astype(int).tolist()}
