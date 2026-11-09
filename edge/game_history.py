"""Persist the latest genuinely pregame score forecast for each fixture."""
from datetime import datetime

def merge_history(history,report):
    rows={p['gameId']:p for p in history.get('projections',[]) if p.get('gameId')}
    for p in report.get('projections',[]):
        stamp=p.get('projectedAt') or report.get('generatedAt')
        try:
            issued=datetime.fromisoformat(stamp.replace('Z','+00:00'))
            kickoff=datetime.fromisoformat(p['kickoff'].replace('Z','+00:00'))
            prior=rows.get(p['gameId']);prior_time=datetime.fromisoformat(prior['projectedAt'].replace('Z','+00:00')) if prior else None
            if issued>=kickoff or prior_time and prior_time>issued:continue
        except (KeyError,TypeError,ValueError):continue
        rows[p['gameId']]={k:v for k,v in p.items() if k!='samples'}|{'projectedAt':stamp}
    return {'projections':sorted(rows.values(),key=lambda p:p.get('kickoff',''),reverse=True)[:600]}
