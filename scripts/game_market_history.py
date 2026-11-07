"""Bounded, source-specific game price observations. Never creates synthetic earlier quotes."""
import datetime as dt
import json
import math
from pathlib import Path
UTC=dt.timezone.utc
MARKETS={'h2h','spreads','totals'}
def finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
def instant(value):
    try:
        parsed=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return parsed.timestamp() if parsed.tzinfo else None
    except (ValueError,TypeError):return None

def identity(row):return tuple(row.get(k) for k in ['homeTeam','awayTeam','kickoff','source','bookKey','market','side'])
def append_history(output,events,observed_at):
    output=Path(output);path=output/'game-market-movement.json'
    try:history=json.loads(path.read_text())
    except (OSError,ValueError):history={'observations':[]}
    stamp=instant(observed_at)
    if stamp is None:return history
    rows=[r for r in history.get('observations',[]) if instant(r.get('observedAt')) is not None];last={}
    for r in sorted(rows,key=lambda r:instant(r['observedAt'])):last[identity(r)]=r
    for event in events:
        kickoff=instant(event.get('commence_time'))
        if kickoff is None:continue
        canonical=dt.datetime.fromtimestamp(kickoff,UTC).isoformat()
        for book in event.get('bookmakers',[]):
            for market in book.get('markets',[]):
                key=market.get('key')
                if key not in MARKETS:continue
                outcomes=market.get('outcomes',[])
                for quote in outcomes:
                    side=quote.get('name');price=quote.get('price');line=quote.get('point') if key!='h2h' else None
                    if side not in (['Over','Under'] if key=='totals' else [event.get('home_team'),event.get('away_team')]):continue
                    if sum(o.get('name')==side for o in outcomes)!=1:continue
                    if not finite(price) or abs(price)<100 or key!='h2h' and not finite(line):continue
                    row={'gameKey':'|'.join([event['home_team'],event['away_team'],canonical]),'eventId':event.get('id'),'homeTeam':event['home_team'],'awayTeam':event['away_team'],'kickoff':canonical,'source':book.get('source') or event.get('source') or 'The Odds API','bookKey':book.get('key') or book.get('title'),'book':book.get('title') or book.get('key'),'market':key,'side':side,'point':line,'price':price,'observedAt':observed_at,'providerUpdatedAt':market.get('last_update') or book.get('last_update'),'sourceObservedAt':market.get('observed_at') or book.get('observed_at')}
                    old=last.get(identity(row))
                    if old and instant(old['observedAt'])>=stamp:continue
                    if old and instant(old.get('providerUpdatedAt')) is not None and instant(row.get('providerUpdatedAt')) is not None and instant(row['providerUpdatedAt'])<instant(old['providerUpdatedAt']):continue
                    if old and old.get('point')==line and old.get('price')==price:continue
                    rows.append(row);last[identity(row)]=row
    rows.sort(key=lambda r:instant(r['observedAt']));rows=[r for r in rows if stamp-instant(r['observedAt'])<=45*86400][-6000:]
    payload={'schemaVersion':1,'generatedAt':observed_at,'observations':rows,'scope':'First archived observation plus subsequent line or price changes per source, book, exact kickoff, market and outcome. Provider times are separate from collection times. Up to 45 days / 6,000 changed quotes. No synthetic opening or closing lines.'}
    output.mkdir(exist_ok=True,parents=True);temp=path.with_suffix('.tmp');temp.write_text(json.dumps(payload,separators=(',',':'),allow_nan=False));temp.replace(path);return payload

def bootstrap(output=Path('data')):
    output=Path(output)
    try:seeded=bool(json.loads((output/'game-market-movement.json').read_text()).get('observations'))
    except (OSError,ValueError):seeded=False
    try:snaps=[] if seeded else json.loads((output/'game-odds-history.json').read_text()).get('snapshots',[])
    except (OSError,ValueError):snaps=[]
    for snapshot in sorted(snaps,key=lambda s:instant(s.get('observedAt')) or 0):append_history(output,snapshot.get('data',[]),snapshot.get('observedAt'))
    for name in ['game-odds','public-game-odds']:
        try:payload=json.loads((output/(name+'.json')).read_text())
        except (OSError,ValueError):continue
        if payload.get('status') in ['ok','no_prices']:append_history(output,payload.get('data',[]),payload.get('generatedAt'))
if __name__=='__main__':bootstrap()
