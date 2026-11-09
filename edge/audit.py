"""Freeze committed pregame forecasts and compare them with subsequently published stats."""
import json
import subprocess
from pathlib import Path
import pandas as pd
from .config import MARKET_SPECS

def publication_record(path):
    """Use a clean tracked file's actual Git commit, not the model run-start timestamp."""
    try:
        if subprocess.run(['git','diff','--quiet','HEAD','--',str(path)],capture_output=True).returncode:
            return None
        result=subprocess.run(['git','log','-1','--format=%H%n%cI','--',str(path)],check=True,capture_output=True,text=True)
        lines=result.stdout.strip().splitlines()
        if len(lines)!=2:return None
        return {'commit':lines[0],'issuedAt':pd.Timestamp(lines[1]).isoformat()}
    except (OSError,subprocess.SubprocessError,ValueError):return None

def update_ledger(existing,snapshot,publication,actuals,season,now):
    """First archived forecast wins; later runs never overwrite its projected value."""
    ledger={r['id']:dict(r) for r in existing if r.get('season')==season}
    if snapshot and snapshot.get('schemaVersion')==3 and publication:
        issued=pd.Timestamp(publication['issuedAt'])
        for f in snapshot.get('forecasts',[]):
            kickoff=pd.Timestamp(f['kickoff'])
            if issued>=kickoff:continue
            game_season,week=map(int,f['gameId'].split('_')[:2])
            if game_season!=season:continue
            for market,m in f.get('marketSamples',{}).items():
                if market not in MARKET_SPECS:continue
                label,family,target=MARKET_SPECS[market]
                key='|'.join([f['gameId'],f['playerId'],market])
                if key in ledger:continue
                ledger[key]={'id':key,'season':season,'week':week,'gameId':f['gameId'],'playerId':f['playerId'],
                    'player':f['name'],'position':f['position'],'team':f['team'],'opponent':f['opponent'],
                    'kickoff':f['kickoff'],'market':market,'target':target,'label':label,
                    'projected':m['mean'],'p10':m.get('p10'),'p90':m.get('p90'),
                    'issuedAt':publication['issuedAt'],'sourceCommit':publication['commit'],
                    'baseline':f.get('features',{}).get(target+'_last6'),'marketPassedAtIssue':m.get('validationPassed',False)}
    lookup={(str(r.game_id),str(r.player_id)):r for r in actuals.itertuples()}
    rows=[]
    for archived in sorted(ledger.values(),key=lambda r:(r['week'],r['player'],r['market'])):
        row=dict(archived);actual=lookup.get((row['gameId'],row['playerId']))
        value=getattr(actual,row['target'],None) if actual is not None else None
        scored=value is not None and pd.notna(value) and pd.Timestamp(row['kickoff'])<now
        row.update({'actual':float(value) if scored else None,'error':float(value)-row['projected'] if scored else None,
            'status':'scored' if scored else 'pending' if pd.Timestamp(row['kickoff'])>now else 'awaiting_stats_or_participation',
            'checkedAt':now.isoformat()})
        rows.append(row)
    return list(ledger.values()),{'schemaVersion':1,'season':season,'generatedAt':now.isoformat(),
        'source':'Archived public forecasts committed before kickoff; first archived value retained.',
        'missingOutcomePolicy':'Missing player statistics are not zero-filled; review participation and void rules.',
        'rows':rows}

def write_audit(directory,frame,season,now):
    ledger_path=directory/f'forecast-ledger-{season}.json'
    existing=json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    snapshot_path=directory/'latest.json'
    snapshot=json.loads(snapshot_path.read_text()) if snapshot_path.exists() else None
    publication=publication_record(snapshot_path) if snapshot_path.exists() else None
    ledger,results=update_ledger(existing,snapshot,publication,frame[~frame.forecast],season,now)
    from .benchmark import attach_benchmarks
    odds_path=directory/'odds.json'
    odds=json.loads(odds_path.read_text()) if odds_path.exists() else {}
    ledger=attach_benchmarks(ledger,odds,now)
    benchmarks={r['id']:r.get('benchmark') for r in ledger}
    for row in results['rows']:
        if benchmarks.get(row['id']):row['benchmark']=benchmarks[row['id']]
    for path,data in [(ledger_path,ledger),(directory/'projection-results.json',results)]:
        temp=path.with_suffix('.json.tmp');temp.write_text(json.dumps(data,separators=(',',':'),allow_nan=False));temp.replace(path)
    return {'archived':len(ledger),'scored':sum(r['status']=='scored' for r in results['rows'])}
