"""Public injury/depth snapshots and experience-aware QB scenarios. No betting settlement assumptions."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import gzip
import io
import json
import re
from pathlib import Path
from urllib.request import Request,urlopen
import numpy as np
import pandas as pd
from .data import BASE,team,normalize_stats
from .markets import FULL_NAMES

TEAM_SITES={'ARI':'azcardinals.com','ATL':'atlantafalcons.com','BAL':'baltimoreravens.com','BUF':'buffalobills.com','CAR':'panthers.com','CHI':'chicagobears.com','CIN':'bengals.com','CLE':'clevelandbrowns.com','DAL':'dallascowboys.com','DEN':'denverbroncos.com','DET':'detroitlions.com','GB':'packers.com','HOU':'houstontexans.com','IND':'colts.com','JAX':'jaguars.com','KC':'chiefs.com','LAC':'chargers.com','LAR':'therams.com','LV':'raiders.com','MIA':'miamidolphins.com','MIN':'vikings.com','NE':'patriots.com','NO':'neworleanssaints.com','NYG':'giants.com','NYJ':'newyorkjets.com','PHI':'philadelphiaeagles.com','PIT':'steelers.com','SEA':'seahawks.com','SF':'49ers.com','TB':'buccaneers.com','TEN':'tennesseetitans.com','WAS':'commanders.com'}
def canonical(name):
    words=re.sub(r'[^a-z0-9 ]','',str(name).lower()).split()
    return ''.join(w for w in words if w not in ['jr','sr','ii','iii','iv'])

def fetch(url,timeout=22):
    with urlopen(Request(url,headers={'User-Agent':'PublicFootballResearch/0.4'}),timeout=timeout) as r:
        raw=r.read();return raw,{'url':url,'observedAt':datetime.now(timezone.utc).isoformat(),'lastModified':r.headers.get('Last-Modified'),'status':'ok'}

def public_csv(tag,name,cache=None,immutable=False):
    path=cache/name if cache else None
    if immutable and path and path.exists():raw=path.read_bytes()
    else:
        raw,_=fetch(BASE+tag+'/'+name,timeout=60)
        if path:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return pd.read_csv(io.BytesIO(gzip.decompress(raw) if name.endswith('.gz') else raw),low_memory=False,dtype={'gsis_id':str,'espn_id':str})

def team_from_heading(text):
    value=canonical(text)
    for code,full in FULL_NAMES.items():
        if value in [canonical(code),canonical(full),canonical(full.split()[-1])]:return code
    return None

def game_status(value):
    text=str(value or '').lower().strip()
    mapping={'questionable':'QUESTIONABLE','doubtful':'DOUBTFUL','out':'OUT','inactive':'INACTIVE','injured reserve':'IR','injured-reserve':'IR','reserve/injured':'IR','active':'ACTIVE'}
    return mapping.get(text,'UNSPECIFIED')

def parse_official(html,url,season,week,observed_at,league=False):
    from bs4 import BeautifulSoup
    soup=BeautifulSoup(html,'html.parser');text=soup.get_text(' ',strip=True)
    year=re.search(r'\b(20\d{2})\s+(?:NFL\s+)?Injury Report',text,re.I)
    wk=re.search(r'\bWEEK\s*[-:]?\s*(\d{1,2})\b',text,re.I)
    if league and (not year or int(year.group(1))!=season or not wk or int(wk.group(1))!=week):
        raise ValueError('Official league report does not match upcoming season/week')
    scope=bool(league or (wk and int(wk.group(1))==week))
    records=[]
    for table in soup.select('table'):
        headers=[h.get_text(' ',strip=True) for h in table.select('thead th')]
        if not headers:headers=[h.get_text(' ',strip=True) for h in table.select('tr th')]
        if 'Player' not in headers or 'Game Status' not in headers:continue
        club=None
        for heading in table.find_all_previous(['h2','h3','h4','h5'],limit=15):
            club=team_from_heading(heading.get_text(' ',strip=True))
            if club:break
        if club is None:
            parent=table.parent
            for _ in range(4):
                if parent is None:break
                for node in parent.select('[alt],h2,h3,h4'):
                    club=team_from_heading(node.get('alt') or node.get_text(' ',strip=True))
                    if club:break
                if club:break
                parent=parent.parent
        if not club:continue
        for tr in table.select('tbody tr'):
            cells=tr.find_all('td',recursive=False)
            if len(cells)!=len(headers):continue
            data=dict(zip(headers,[c.get_text(' ',strip=True) for c in cells]))
            name=data.get('Player','').strip();a=cells[headers.index('Player')].select_one('a')
            if a:name=a.get_text(' ',strip=True)
            if not name:continue
            practice=data.get('Practice Status') or next((data.get(day) for day in ['Sun','Sat','Fri','Thu','Wed','Tue','Mon'] if data.get(day)),None)
            records.append({'name':name,'team':club,'position':data.get('Position'),'gameStatus':game_status(data['Game Status']),
                'practice':practice,'injury':data.get('Injuries',data.get('Injury','')),'source':url,'authority':'official',
                'scopeVerified':scope,'season':season,'week':week,'observedAt':observed_at,'reportedAt':None})
    if league and not records:raise ValueError('No identifiable official injury tables')
    return records

def parse_espn(payload,season,week,observed_at):
    records=[]
    groups=payload.get('injuries',payload.get('teams',[]))
    if not isinstance(groups,list):raise ValueError('ESPN schema changed')
    for group in groups:
        club=team(group.get('abbreviation') or group.get('team',{}).get('abbreviation',''))
        if club not in FULL_NAMES:club=team_from_heading(group.get('displayName',group.get('team',{}).get('displayName','')))
        for injury in group.get('injuries',[]):
            athlete=injury.get('athlete',{});status=injury.get('status',injury.get('type',{}).get('description',''))
            if isinstance(status,dict):status=status.get('name') or status.get('type') or status.get('description')
            rawdate=injury.get('date');reported=pd.to_datetime(rawdate,utc=True,errors='coerce')
            observed=pd.Timestamp(observed_at)
            if pd.notna(reported) and (reported>observed or observed-reported>pd.Timedelta(days=14)):continue
            if not club or not athlete.get('displayName'):continue
            details=injury.get('details',{})
            records.append({'name':athlete['displayName'],'espnId':str(athlete.get('id','')),'team':club,'position':athlete.get('position',{}).get('abbreviation'),
                'gameStatus':game_status(status),'practice':None,'returnComment':injury.get('longComment',injury.get('shortComment','')),'injury':details.get('type',injury.get('shortComment','')),
                'source':'https://www.espn.com/nfl/injuries','authority':'secondary','scopeVerified':False,
                'season':season,'week':week,'observedAt':observed_at,'reportedAt':reported.isoformat() if pd.notna(reported) else None})
    return records

def latest_depth(frame,now):
    needed={'dt','team','player_name','gsis_id','pos_abb','pos_slot','pos_rank'}
    if not needed.issubset(frame):raise ValueError('Depth-chart schema changed')
    d=frame.copy();d['stamp']=pd.to_datetime(d.dt,utc=True,errors='coerce')
    d=d[d.stamp.notna() & (d.stamp<=now)];d['team']=d.team.map(team)
    latest=d.groupby('team').stamp.transform('max');d=d[d.stamp.eq(latest)&d.pos_abb.isin(['QB','RB','WR','TE'])]
    out=[]
    for r in d.to_dict('records'):
        if pd.isna(r['pos_rank']) or pd.isna(r['gsis_id']):continue
        out.append({'playerId':str(r['gsis_id']),'espnId':str(r.get('espn_id','')),'name':r['player_name'],'team':r['team'],'position':r['pos_abb'],
            'slot':int(r['pos_slot']),'rank':int(r['pos_rank']),'asOf':r['stamp'].isoformat(),
            'fresh':bool(now-r['stamp']<=pd.Timedelta(hours=72)),
            'source':'https://github.com/nflverse/nflverse-data/releases/tag/depth_charts','sourceLabel':'ESPN depth charts via nflverse'})
    return out

def match_and_resolve(records,depth,profiles,season,week,now):
    by_name={};by_espn={}
    for p in [*profiles,*depth]:
        key=(p['team'],canonical(p['name']));by_name.setdefault(key,set()).add(p['playerId'])
        if p.get('espnId'):by_espn.setdefault((p['team'],str(p['espnId'])),set()).add(p['playerId'])
    grouped={};unmatched=0
    for r in records:
        ids=by_espn.get((r['team'],r.get('espnId',''))) or by_name.get((r['team'],canonical(r['name'])),set())
        if len(ids)!=1:unmatched+=1;continue
        key=next(iter(ids));grouped.setdefault(key,[]).append(r)
    result={}
    for pid,items in grouped.items():
        fresh=[r for r in items if r['season']==season and r['week']==week and 0<=(now-pd.Timestamp(r['observedAt'])).total_seconds()<=7200]
        official=[r for r in fresh if r['authority']=='official' and r['scopeVerified']]
        specific=[r for r in official if r['gameStatus']!='UNSPECIFIED']
        conflicts=len({r['gameStatus'] for r in specific})>1
        selected=(specific or official or fresh or items)[-1]
        secondary=[r for r in fresh if r['authority']=='secondary' and r['gameStatus']!='UNSPECIFIED']
        status=selected['gameStatus']
        if status=='UNSPECIFIED' and secondary:status=secondary[-1]['gameStatus']
        confirmed=bool(specific and not conflicts)
        out=confirmed and status in ['OUT','INACTIVE','IR']
        caution=status in ['QUESTIONABLE','DOUBTFUL','OUT','IR','INACTIVE'] or conflicts
        practice=next((r['practice'] for r in reversed(official) if r.get('practice')),None)
        if practice and ('limited' in practice.lower() or practice.upper() in ['LP','DNP'] or 'did not' in practice.lower()):caution=True
        result[pid]={'status':status,'label':{'UNSPECIFIED':'No game designation','IR':'Injured reserve'}.get(status,status.title().replace('_',' ')),'practice':practice,'injury':selected.get('injury'),
            'confirmed':confirmed,'ruledOut':out,'conflict':conflicts,'reviewRequired':caution,
            'season':season,'week':week,'observedAt':selected['observedAt'],'sources':items,'note':'Practice participation is not a game-status designation.'}
    return result,unmatched

def roster_roles(depth,injuries):
    groups={}
    for row in depth:groups.setdefault((row['team'],row['position'],row['slot']),[]).append(row)
    output=[]
    for rows in groups.values():
        rows=sorted(rows,key=lambda r:r['rank']);active=[r for r in rows if not injuries.get(r['playerId'],{}).get('ruledOut')]
        expected=active[0]['playerId'] if active and rows[0]['fresh'] else None
        for row in rows:
            p=dict(row);p['listedStarter']=row['rank']==1;p['expectedStarter']=row['playerId']==expected
            p['replacement']=p['expectedStarter'] and row['rank']>1
            p['roleLabel']='Next on depth chart; first string ruled out' if p['replacement'] else 'Listed starter' if p['listedStarter'] else 'Backup'
            p['health']=injuries.get(row['playerId'],{'status':'NOT_LISTED','label':'No status reported','ruledOut':False,'reviewRequired':False,'confirmed':False,'sources':[]})
            output.append(p)
    return output

def qb_replacement_parameters(games,stats,season):
    """Historical QB-change cohorts, trained only on seasons before the current one."""
    entries=[]
    for g in games[games.season.between(1999,season)].to_dict('records'):
        if g.get('game_type')!='REG' or pd.isna(g.get('home_score')):continue
        for side in ['home','away']:
            pid=g.get(side+'_qb_id')
            if not isinstance(pid,str) or not pid:continue
            entries.append({'gameId':g['game_id'],'playerId':pid,'team':team(g[side+'_team']),'season':int(g['season']),'week':int(g['week']),'date':str(g['gameday'])})
    starts=pd.DataFrame(entries)
    if starts.empty:return {'groups':{},'players':{},'trainingThrough':season-1,'reason':'No public starting-QB identifiers'}
    qb=stats[stats.position.eq('QB')].copy();qb['team']=qb.team.map(team)
    starts=starts.merge(qb[['player_id','season','week','team','passing_yards']],left_on=['playerId','season','week','team'],right_on=['player_id','season','week','team'],how='left').sort_values(['date','gameId'])
    experienced={};team_history={};ratios={'limited':[],'experienced':[]};player_games={}
    for r in starts.to_dict('records'):
        pid=r['playerId'];past=team_history.setdefault(r['team'],[]);count=experienced.get(pid,0)
        if len(past)>=3 and pd.notna(r['passing_yards']):
            usual=max(set(x['playerId'] for x in past[-3:]),key=lambda p:sum(x['playerId']==p for x in past[-3:]))
            values=[x['passing_yards'] for x in past[-6:] if pd.notna(x['passing_yards'])];baseline=np.mean(values) if values else np.nan
            if 2021<=r['season']<season and pid!=usual and sum(x['playerId']==usual for x in past[-3:])>=2 and baseline>=100:
                ratios['experienced' if count>=8 else 'limited'].append(float(r['passing_yards'])/baseline)
        experienced[pid]=count+1;past.append(r);player_games.setdefault(pid,[]).append(r['passing_yards'])
    groups={k:{'n':len(v),'ratio':float(np.median(v)) if len(v)>=15 else None,'p25':float(np.quantile(v,.25)) if v else None,'p75':float(np.quantile(v,.75)) if v else None} for k,v in ratios.items()}
    players={pid:{'recordedStarts':experienced[pid],'recentStartYards':[float(v) for v in values[-10:] if pd.notna(v)]} for pid,values in player_games.items()}
    return {'groups':groups,'players':players,'trainingThrough':season-1,'note':'Observational QB changes; not a causal or current-season validated injury model.'}

def qb_scenarios(bundle,roles,injuries,parameters):
    scenarios={};by_team={}
    for r in roles:
        if r['position']=='QB':by_team.setdefault(r['team'],[]).append(r)
    for club,rows in by_team.items():
        rows=sorted(rows,key=lambda r:r['rank']);first=next((r for r in rows if r['rank']==1 and r['fresh']),None)
        if not first:continue
        health=injuries.get(first['playerId'],{})
        if health.get('status') not in ['QUESTIONABLE','DOUBTFUL','OUT','INACTIVE','IR']:continue
        backup=next((r for r in rows if r['playerId']!=first['playerId'] and not injuries.get(r['playerId'],{}).get('ruledOut')),None)
        if not backup:continue
        reference=next((f for f in bundle['forecasts'] if f['playerId']==first['playerId'] and f.get('marketSamples',{}).get('player_pass_yds')),None)
        if not reference or health.get('week') is not None and int(reference['gameId'].split('_')[1])!=health['week']:continue
        baseline=reference['marketSamples']['player_pass_yds']['mean'];info=parameters.get('players',{}).get(backup['playerId'],{'recordedStarts':0,'recentStartYards':[]})
        group='experienced' if info['recordedStarts']>=8 else 'limited';estimate=parameters.get('groups',{}).get(group,{})
        if baseline<80 or estimate.get('ratio') is None:continue
        group_ratio=estimate['ratio'];own=info['recentStartYards'];weight=len(own)/(len(own)+5)
        expected=weight*np.mean(own)+(1-weight)*baseline*group_ratio if own else baseline*group_ratio
        ratio=float(expected/baseline)
        if not .25<=ratio<=1.75:continue
        scenarios[club]={'team':club,'starterId':first['playerId'],'starterName':first['name'],'backupId':backup['playerId'],'backupName':backup['name'],
            'ownStartMean':float(np.mean(own)) if own else None,'ownWeight':weight,'groupRatio':group_ratio,'backupRecordedStarts':info['recordedStarts'],'startsCoverage':'Public schedule history since 1999 where QB IDs are available; recent production since 2021',
            'experienceGroup':group,'comparisonGames':estimate['n'],'passingYardsFactor':ratio,'baselinePassingYards':baseline,'backupPassingYards':float(expected),
            'applyAutomatically':bool(health.get('ruledOut') and not health.get('conflict')),'triggerStatus':health.get('status'),
            'reason':'Replacement estimate blends the QB’s recorded starting-game production with an experience-matched historical QB-change cohort.',
            'validated':False,'gameId':reference['gameId'],'kickoff':reference['kickoff']}
    return scenarios

def run(directory,now=None):
    now=pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now);bundle=json.loads((directory/'latest.json').read_text());season=bundle['season']
    future=sorted([f for f in bundle['forecasts'] if pd.Timestamp(f['kickoff'])>now],key=lambda f:f['kickoff'])
    if not future:raise ValueError('No future model games; no current injury snapshot can be scoped')
    week=int(future[0]['gameId'].split('_')[1]);clubs={f['team'] for f in future if int(f['gameId'].split('_')[1])==week};cache=Path('work/health-cache')
    errors=[];sources=[];records=[]
    def official_job(url,league=False):
        try:
            raw,meta=fetch(url);rows=parse_official(raw.decode(),url,season,week,meta['observedAt'],league)
            meta['records']=len(rows);return rows,meta,None
        except Exception as e:return [],{'url':url,'status':'unavailable','error':type(e).__name__},str(e)[:200]
    jobs=[('https://www.nfl.com/injuries/',True)]+[('https://www.'+TEAM_SITES[t]+'/team/injury-report/',False) for t in sorted(clubs)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for rows,meta,error in pool.map(lambda args:official_job(*args),jobs):records.extend(rows);sources.append(meta)
    try:
        raw,meta=fetch('https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries');rows=parse_espn(json.loads(raw),season,week,meta['observedAt']);records.extend(rows);meta['records']=len(rows);sources.append(meta)
    except Exception as e:sources.append({'url':'https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries','status':'unavailable','error':type(e).__name__})
    depth=latest_depth(public_csv('depth_charts',f'depth_charts_{season}.csv.gz',cache),now)
    records=[r for r in records if r['team'] in clubs]
    injuries,unmatched=match_and_resolve(records,depth,bundle.get('players',[]),season,week,now);roles=roster_roles(depth,injuries)
    games=public_csv('schedules','games.csv',cache)
    stats=[]
    for year in range(2021,season+1):stats.append(normalize_stats(public_csv('stats_player',f'stats_player_week_{year}.csv.gz',cache,immutable=year<season),positions=['QB']))
    params=qb_replacement_parameters(games,pd.concat(stats,ignore_index=True),season)
    scenarios=qb_scenarios(bundle,roles,injuries,params)
    trade_notes={};team_mapping={r['playerId']:r['team'] for r in depth if r['fresh']}
    try:
        from .context import current_team_map
        people=public_csv('players','players.csv.gz',cache)
        raw,_=fetch('https://raw.githubusercontent.com/nflverse/nfldata/master/data/trades.csv')
        team_mapping,trade_notes=current_team_map(depth,pd.read_csv(io.BytesIO(raw)),people,now)
    except Exception as e:errors.append('Trade feed: '+type(e).__name__)
    snapshot={'schemaVersion':1,'generatedAt':now.isoformat(),'season':season,'week':week,'modelGeneratedAt':bundle['generatedAt'],
        'sources':sources,'injuryReports':records,'injuries':injuries,'roster':roles,'qbScenarios':scenarios,'qbExperienceParameters':{'groups':params['groups'],'trainingThrough':params['trainingThrough']},
        'currentTeams':team_mapping,'trades':trade_notes,'errors':errors,'unmatchedInjuryRecords':unmatched,'scope':'Current public injury/depth information. Not a historically calibrated injury adjustment.',
        'officialRecords':sum(r['authority']=='official' and r['scopeVerified'] for r in records),
        'limitations':['Not listed does not confirm active status.','Practice DNP/LP is not a game designation.','Questionable/Doubtful do not imply a numerical participation probability.','QB-change adjustments are separate observational scenarios.']}
    from .return_reports import collect
    snapshot['returnReports']=collect(bundle,snapshot,now.to_pydatetime())
    from .workload import build_context
    snapshot['workloadContext']=build_context(bundle,snapshot,now.to_pydatetime())
    old=json.loads((directory/'availability.json').read_text()) if (directory/'availability.json').exists() else {}
    history_path=directory/'availability-history.json';history=json.loads(history_path.read_text()) if history_path.exists() else []
    for pid,health in injuries.items():
        before=old.get('injuries',{}).get(pid,{})
        if (before.get('status'),before.get('ruledOut'),before.get('practice'))!=(health['status'],health['ruledOut'],health['practice']):
            history.append({'observedAt':snapshot['generatedAt'],'playerId':pid,'from':before.get('status','UNKNOWN'),'to':health['status'],'ruledOut':health['ruledOut'],'sources':list(dict.fromkeys(r['source'] for r in health['sources']))})
    for club,scenario in scenarios.items():
        before=old.get('qbScenarios',{}).get(club,{})
        if before.get('backupId')!=scenario['backupId'] or before.get('applyAutomatically')!=scenario['applyAutomatically'] or abs(before.get('passingYardsFactor',scenario['passingYardsFactor'])-scenario['passingYardsFactor'])>.001:
            history.append({'observedAt':snapshot['generatedAt'],'type':'qb_projection_update','team':club,'backupId':scenario['backupId'],
                'previousBackupPassingYards':before.get('backupPassingYards'),'backupPassingYards':scenario['backupPassingYards'],
                'usualStarterPassingYards':scenario['baselinePassingYards'],'automaticallyApplied':scenario['applyAutomatically'],'note':'Model scenario movement, not a sportsbook price change.'})
    for path,value in [(directory/'availability.json',snapshot),(history_path,history[-3000:])]:
        tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(value,separators=(',',':'),allow_nan=False));tmp.replace(path)
    return {'injuryPlayers':len(injuries),'rosterRows':len(roles),'officialRecords':snapshot['officialRecords'],'qbScenarios':scenarios,'sourceFailures':sum(s['status']!='ok' for s in sources)}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,default=Path('data'));a=p.parse_args();print(json.dumps(run(a.data),indent=2))
