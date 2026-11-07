"""Published season route efficiency; never substituted for weekly route observations."""
import json
from pathlib import Path
import pandas as pd
from edge.data import get,sumer_snapshot,team

def run():
    now=pd.Timestamp.now(tz='UTC');season=now.year if now.month>=3 else now.year-1
    sources=[];players=[]
    for position,slug in [('WR','wide-receiver'),('TE','tight-end')]:
        url=f'https://sumersports.com/players/{slug}/'
        try:
            raw,_=get(url);snapshot=sumer_snapshot(raw.decode(),url);stamp=pd.Timestamp(snapshot['asOf'])
            if not pd.Timestamp(f'{season}-08-01',tz='UTC')<=stamp<=now or now-stamp>pd.Timedelta(days=7):raise ValueError('Stale or out-of-season snapshot')
            for row in snapshot['players']:
                routes=row.get('Routes Run');yards=row.get('Rec. Yards')
                if routes is None or routes<=0 or yards is None:continue
                players.append({'slug':row['profileUrl'].rstrip('/').split('/')[-1],'team':team(row['label'].split()[0]),'position':position,'season':season,'routes':routes,'receivingYards':yards,'yardsPerRouteRun':yards/routes,'asOf':snapshot['asOf'],'source':url})
            sources.append({'source':url,'status':'ok','asOf':snapshot['asOf']})
        except Exception as error:sources.append({'source':url,'status':'unavailable','error':type(error).__name__})
    path=Path(__file__).resolve().parents[1]/'data/route-research.json'
    path.write_text(json.dumps({'generatedAt':now.isoformat(),'season':season,'players':players,'sources':sources,'scope':'Season aggregate receiving yards divided by actual routes from the same published snapshot. No weekly route estimates or historical backfill.'},separators=(',',':'),allow_nan=False))
    print(f'Published {len(players)} WR/TE route records')
if __name__=='__main__':run()
