"""Optional PostgreSQL persistence. Public GitHub snapshots work without a database account."""
import json
import os
from pathlib import Path
import datetime as dt
from psycopg.types.json import Jsonb
ROOT=Path(__file__).resolve().parents[1]

def sync(directory=None):
    import psycopg
    url=os.environ.get('DATABASE_URL')
    if not url:return {'status':'snapshot_mode','reason':'DATABASE_URL is not configured; DuckDB/Parquet and public JSON remain persistent artifacts.'}
    directory=directory or ROOT/'data'
    def read(name,default):
        try:return json.loads((directory/name).read_text())
        except (OSError,ValueError):return default
    bundle=read('latest.json',{});games=read('upcoming-games.json',{}).get('games',[])
    with psycopg.connect(url) as connection:
        connection.execute((Path(__file__).parent/'migrations/001_initial.sql').read_text())
        teams=set(p.get('team') for p in bundle.get('players',[]) if p.get('team'))|set(t for g in games for t in [g['home_team'],g['away_team']])
        for team in teams:connection.execute('INSERT INTO teams(id,name) VALUES(%s,%s) ON CONFLICT(id) DO NOTHING',(team,team))
        for p in bundle.get('players',[]):connection.execute('INSERT INTO players(id,team_id,name,position) VALUES(%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET team_id=EXCLUDED.team_id,name=EXCLUDED.name,position=EXCLUDED.position',(p['playerId'],p.get('team'),p['name'],p.get('position')))
        for g in games:connection.execute('INSERT INTO games(id,season,week,home_team,away_team,kickoff,venue) VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET kickoff=EXCLUDED.kickoff',(g['game_id'],g['season'],g['week'],g['home_team'],g['away_team'],g['kickoff'],Jsonb({k:g.get(k) for k in ['stadium','roof','surface','location']})))
        version=bundle.get('generatedAt')
        if version:
            connection.execute('INSERT INTO model_versions(id,created_at,configuration,validation) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',(version,version,Jsonb({'name':bundle.get('model'),'features':bundle.get('featureNamesByFamily')}),Jsonb(bundle.get('validationGates',{}))))
            ids={g['game_id'] for g in games}
            for f in bundle.get('forecasts',[]):
                if f['gameId'] not in ids:continue
                connection.execute('INSERT INTO features(player_id,game_id,as_of,values) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',(f['playerId'],f['gameId'],version,Jsonb(f.get('features',{}))))
                for market,m in f.get('marketSamples',{}).items():connection.execute('INSERT INTO predictions(model_version,player_id,game_id,market,issued_at,mean,quantiles,validation_passed) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',(version,f['playerId'],f['gameId'],market,version,m['mean'],Jsonb({'p10':m.get('p10'),'p90':m.get('p90')}),bool(m.get('validationPassed'))))
        for event in read('odds.json',{}).get('data',[]):
            for book in event.get('bookmakers',[]):
                for market in book.get('markets',[]):
                    for o in market.get('outcomes',[]):
                        if o.get('name') not in ['Over','Under']:continue
                        connection.execute('INSERT INTO odds_snapshots(provider_event_id,player_name,book,market,side,line,american_price,observed_at,provider_updated_at,raw) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',(event['id'],o.get('description',''),book['title'],market['key'],o['name'],o.get('point'),o['price'],event.get('collectedAt'),market.get('last_update',book.get('last_update')),Jsonb(o)))
        connection.execute('INSERT INTO ingestion_runs(started_at,completed_at,provider,status,details) VALUES(now(),now(),%s,%s,%s)',('normalized_snapshot_sync','ok',Jsonb({'model':version,'games':len(games)})))
    return {'status':'ok','games':len(games),'modelVersion':version}
if __name__=='__main__':
    try:print(json.dumps(sync()))
    except Exception as error:print(json.dumps({'status':'unavailable','error':type(error).__name__}));raise SystemExit(1)
