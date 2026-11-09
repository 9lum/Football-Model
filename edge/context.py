"""Point-in-time defensive features and current roster/trade reconciliation."""
import io
import re
from pathlib import Path
import numpy as np
import pandas as pd
from .data import BASE,get,team

PBP_COLUMNS=['game_id','play_id','no_play','season','week','season_type','defteam','posteam','qb_dropback','pass_attempt','rush_attempt','qb_kneel','epa','success','sack','qb_hit','yards_gained','passing_yards','receiving_yards','receiver_player_id','complete_pass','defense_man_zone_type','was_pressure','number_of_pass_rushers']
PART_COLUMNS=['nflverse_game_id','game_id','play_id','defense_man_zone_type','was_pressure','number_of_pass_rushers']

def parquet_asset(tag,name,columns,cache,immutable=False):
    import pyarrow.parquet as pq
    path=cache/name;path.parent.mkdir(parents=True,exist_ok=True)
    if immutable and path.exists():raw=path.read_bytes()
    else:
        url=BASE+tag+'/'+name
        if not immutable and tag=='pbp':
            from datetime import datetime,timezone
            url+='?asof='+datetime.now(timezone.utc).strftime('%Y%m%d%H')
        raw,_=get(url);path.write_bytes(raw)
    source=io.BytesIO(raw);available=pq.read_schema(source).names;source.seek(0)
    return pq.read_table(source,columns=[c for c in columns if c in available]).to_pandas()

def summarize_defense(pbp,participation=None):
    d=pbp.copy()
    if participation is not None and not participation.empty:
        p=participation.rename(columns={'nflverse_game_id':'game_id'}).copy()
        if p.duplicated(['game_id','play_id']).any():p=p.drop_duplicates(['game_id','play_id'])
        for key in ['defense_man_zone_type','was_pressure','number_of_pass_rushers']:
            if key in p and key in d:d=d.drop(columns=key)
        d=d.merge(p,on=['game_id','play_id'],how='left',validate='many_to_one')
    if 'season_type' in d:d=d[d.season_type.eq('REG')]
    if 'no_play' in d:d=d[~d.no_play.eq(1)]
    d=d[d.defteam.notna()].copy();d['defteam']=d.defteam.map(team)
    for c in ['qb_dropback','rush_attempt','qb_kneel','epa','sack','qb_hit','yards_gained','complete_pass']:
        if c not in d:d[c]=np.nan
        d[c]=pd.to_numeric(d[c],errors='coerce')
    if 'defense_man_zone_type' not in d:d['defense_man_zone_type']=None
    rows=[]
    for (game,season,week,club),g in d.groupby(['game_id','season','week','defteam']):
        passing=g[g.qb_dropback.eq(1)];rushing=g[g.rush_attempt.eq(1)&~g.qb_kneel.eq(1)]
        coverage=passing.defense_man_zone_type.fillna('').str.upper();known=coverage.isin(['MAN_COVERAGE','ZONE_COVERAGE','MAN','ZONE'])
        rows.append({'game_id':game,'season':int(season),'week':int(week),'team':club,
            'pass_epa_allowed':passing.epa.mean(),'rush_epa_allowed':rushing.epa.mean(),
            'pass_success_allowed':(passing.epa.dropna()>0).mean(),'rush_success_allowed':(rushing.epa.dropna()>0).mean(),
            'sack_rate':passing.sack.mean(),'qb_contact_rate':passing[['sack','qb_hit']].max(axis=1).mean(),
            'explosive_pass_rate':(passing.yards_gained.dropna()>=20).mean(),'explosive_rush_rate':(rushing.yards_gained.dropna()>=10).mean(),
            'man_count':int(coverage.isin(['MAN_COVERAGE','MAN']).sum()),'zone_count':int(coverage.isin(['ZONE_COVERAGE','ZONE']).sum()),'dropbacks':len(passing),
            'pressure_rate':pd.to_numeric(passing.get('was_pressure',pd.Series(dtype=float)),errors='coerce').mean(),
            'five_plus_rusher_rate':(pd.to_numeric(passing.number_of_pass_rushers,errors='coerce').dropna()>=5).mean() if 'number_of_pass_rushers' in passing else np.nan})
    receiver=[]
    if 'receiver_player_id' in d:
        targets=d[d.receiver_player_id.notna() & d.qb_dropback.eq(1)].copy()
        targets['coverage']=targets.defense_man_zone_type.fillna('').str.upper().map({'MAN_COVERAGE':'man','MAN':'man','ZONE_COVERAGE':'zone','ZONE':'zone'})
        targets=targets[targets.coverage.notna()]
        for (season,pid,coverage),g in targets.groupby(['season','receiver_player_id','coverage']):
            receiver.append({'season':int(season)+1,'player_id':pid,'coverage':coverage,'targets':len(g),'yards':float(g.yards_gained.fillna(0).sum())})
    return pd.DataFrame(rows),pd.DataFrame(receiver)

def collect_defense(start,season,cache):
    games=[];receivers=[];sources=[]
    for year in range(start,season+1):
        try:pbp=parquet_asset('pbp',f'play_by_play_{year}.parquet',PBP_COLUMNS,cache,immutable=year<season)
        except Exception as e:sources.append({'season':year,'status':'unavailable','error':type(e).__name__});continue
        part=None
        if year<season:
            try:part=parquet_asset('pbp_participation',f'pbp_participation_{year}.parquet',PART_COLUMNS,cache,immutable=True)
            except Exception:pass
        g,r=summarize_defense(pbp,part);games.append(g)
        if not r.empty:receivers.append(r)
        sources.append({'season':year,'status':'ok','games':len(g),'coverageLabeledDropbacks':int((g.man_count+g.zone_count).sum()),'currentSeasonCoverageLagExpected':year==season,'pbpSource':BASE+'pbp/'+f'play_by_play_{year}.parquet','participationSource':BASE+'pbp_participation/'+f'pbp_participation_{year}.parquet' if part is not None else None})
    return pd.concat(games,ignore_index=True) if games else pd.DataFrame(),pd.concat(receivers,ignore_index=True) if receivers else pd.DataFrame(),sources

def parse_coverage(html,now):
    from bs4 import BeautifulSoup
    from .availability import team_from_heading
    soup=BeautifulSoup(html,'html.parser');published=soup.select_one('time[datetime]')
    if published:stamp=pd.to_datetime(published['datetime'],utc=True,errors='coerce')
    else:
        match=re.search(r'20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:?\d{2}|Z)',html)
        stamp=pd.to_datetime(match.group(0),utc=True,errors='coerce') if match else pd.NaT
    if pd.isna(stamp) or stamp>now or now-stamp>pd.Timedelta(days=10):raise ValueError('Coverage snapshot is missing a fresh publication date')
    output={}
    for table in soup.select('table'):
        headers=[c.get_text(' ',strip=True) for c in table.select('thead th')]
        if not headers:headers=[c.get_text(' ',strip=True) for c in table.select('tr')[0].select('th,td')] if table.select('tr') else []
        if not {'Team','Man Rate','Zone Rate'}.issubset(headers):continue
        for tr in table.select('tr'):
            cells=tr.select('td')
            if len(cells)!=len(headers):continue
            row=dict(zip(headers,[c.get_text(' ',strip=True) for c in cells]));club=team_from_heading(row['Team'])
            if not club:continue
            man=float(row['Man Rate'].strip('%'))/100;zone=float(row['Zone Rate'].strip('%'))/100
            if not 0<man+zone<=1.01:continue
            output[club]={'man':man,'zone':zone,'asOf':stamp.isoformat(),'source':'https://www.sharpfootballanalysis.com/stats-nfl/nfl-coverage-schemes/'}
    if not output:raise ValueError('Public coverage table missing or inaccessible')
    return output

def attach_defense(frame,features,game_defense,receiver_priors,schedules,current_coverage=None):
    if game_defense.empty:return frame,features
    d=frame.copy();context=game_defense.merge(schedules[['game_id','team','kickoff']].drop_duplicates(),on=['game_id','team'],how='inner',validate='many_to_one').sort_values('kickoff')
    numeric=['pass_epa_allowed','rush_epa_allowed','pass_success_allowed','rush_success_allowed','sack_rate','qb_contact_rate','explosive_pass_rate','explosive_rush_rate','pressure_rate','five_plus_rusher_rate']
    prior=context.groupby(['season','team'])[['man_count','zone_count','dropbacks']].sum();receiver_lookup={}
    if not receiver_priors.empty:
        totals=receiver_priors.groupby(['season','coverage'])[['yards','targets']].sum()
        for row in receiver_priors.itertuples():
            league=totals.loc[(row.season,row.coverage)];mean=league.yards/max(league.targets,1)
            receiver_lookup[(row.season,row.player_id,row.coverage)]=(row.yards+30*mean)/(row.targets+30)
    values=[]
    keys=d[['game_id','opponent_team','kickoff','season','forecast']].drop_duplicates()
    for r in keys.itertuples():
        history=context[(context.team==r.opponent_team)&(context.kickoff<r.kickoff)].tail(6)
        record={'game_id':r.game_id,'opponent_team':r.opponent_team}
        record.update({'matchup_'+key:history[key].mean() for key in numeric})
        cov=prior.loc[(r.season-1,r.opponent_team)] if (r.season-1,r.opponent_team) in prior.index else None
        labeled=0 if cov is None else cov.man_count+cov.zone_count
        record['matchup_man_rate']=cov.man_count/cov.dropbacks if cov is not None and labeled>=100 else np.nan
        record['matchup_zone_rate']=cov.zone_count/cov.dropbacks if cov is not None and labeled>=100 else np.nan
        if r.forecast and current_coverage and r.opponent_team in current_coverage:
            current=current_coverage[r.opponent_team]
            if pd.Timestamp(current['asOf'])<r.kickoff:record['matchup_man_rate']=current['man'];record['matchup_zone_rate']=current['zone']
        values.append(record)
    d=d.merge(pd.DataFrame(values).drop_duplicates(['game_id','opponent_team']),on=['game_id','opponent_team'],how='left',validate='many_to_one')
    d['coverage_receiver_man_ypt']=[receiver_lookup.get((r.season,r.player_id,'man'),np.nan) for r in d.itertuples()]
    d['coverage_receiver_zone_ypt']=[receiver_lookup.get((r.season,r.player_id,'zone'),np.nan) for r in d.itertuples()]
    d['coverage_expected_ypt']=d.matchup_man_rate*d.coverage_receiver_man_ypt+d.matchup_zone_rate*d.coverage_receiver_zone_ypt
    added=[c for c in d if c.startswith('matchup_') or c.startswith('coverage_')]
    return d,features+added

def current_team_map(depth,trades,players,now):
    mapping={};trade_notes={}
    for r in depth:
        if r['fresh']:mapping[r['playerId']]=r['team']
    if trades is None or trades.empty:return mapping,trade_notes
    pfr='pfr_id' if 'pfr_id' in players else None
    if not pfr or 'gsis_id' not in players:return mapping,trade_notes
    cross=players[[pfr,'gsis_id']].dropna().drop_duplicates();cross=cross[~cross[pfr].duplicated(keep=False)].set_index(pfr).gsis_id.to_dict()
    t=trades.copy();t['date']=pd.to_datetime(t.trade_date,utc=True,errors='coerce')
    t=t[t.date.notna() & (t.date<=now)]
    if 'pick_season' in t:t=t[t.pick_season.isna()]
    for r in t.sort_values('date').to_dict('records'):
        pid=cross.get(r.get('pfr_id'))
        if not pid:continue
        destination=team(r['received']);origin=team(r['gave'])
        if r['date']<pd.Timestamp(f'{now.year if now.month>=3 else now.year-1}-01-01',tz='UTC'):continue
        trade_notes[pid]={'from':origin,'to':destination,'date':r['date'].isoformat(),'source':'https://github.com/nflverse/nfldata/blob/master/data/trades.csv','corroboratedByDepth':mapping.get(pid)==destination}
        latest_depth=next((pd.Timestamp(x['asOf']) for x in depth if x['playerId']==pid and x['fresh']),None)
        if latest_depth is None or r['date'].normalize()>=latest_depth.normalize():mapping[pid]=destination
    return mapping,trade_notes
