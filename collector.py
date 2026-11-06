"""Run continuously on an always-on host. Credentials are environment variables only."""
import datetime as dt
import json
import os
import sqlite3
import time
import urllib.request
import urllib.error

DB = os.environ.get('EDGE_DB', 'edge-history.sqlite')
BASE = 'https://api.the-odds-api.com/v4/sports/americanfootball_nfl/'

def fetch(url, token=None):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer '+token} if token else {})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)

def collect(db):
    from urllib.parse import urlencode
    key = os.environ.get('ODDS_API_KEY')
    if not key:
        raise ValueError('ODDS_API_KEY is required')
    now = dt.datetime.now(dt.timezone.utc)
    params = {'apiKey': key}
    events = fetch(BASE+'events?'+urlencode(params))
    hours = float(os.environ.get('LOOKAHEAD_HOURS', '48'))
    for event in events:
        start = dt.datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
        if not 0 < (start-now).total_seconds() < hours*3600:
            continue
        query = {**params, 'regions': 'us,us2,eu', 'markets': 'player_receptions,player_reception_yds,player_rush_yds,player_rush_attempts,player_rush_tds,player_pass_yds,player_pass_attempts,player_pass_completions,player_pass_tds,player_pass_interceptions,player_reception_tds', 'oddsFormat': 'american'}
        odds = fetch(BASE+'events/'+event['id']+'/odds?'+urlencode(query))
        db.execute('INSERT INTO snapshots VALUES (?,?,?,?)', (now.isoformat(), 'odds', event['id'], json.dumps(odds)))
        db.commit()
    if os.environ.get('STATS_FEED_URL'):
        stats = fetch(os.environ['STATS_FEED_URL'], os.environ.get('STATS_FEED_TOKEN'))
        if not stats.get('asOf') or not isinstance(stats.get('players'), list):
            raise ValueError('Invalid normalized statistics feed')
        db.execute('INSERT INTO snapshots VALUES (?,?,?,?)', (now.isoformat(), 'stats', '', json.dumps(stats)))
        db.commit()

def main():
    db = sqlite3.connect(DB)
    db.execute('CREATE TABLE IF NOT EXISTS snapshots (observed_at TEXT, kind TEXT, event_id TEXT, payload TEXT)')
    db.execute('CREATE INDEX IF NOT EXISTS event_time ON snapshots(event_id, observed_at)')
    interval = max(60, int(os.environ.get('POLL_SECONDS', '60')))
    while True:
        try:
            collect(db)
            print(dt.datetime.now(dt.timezone.utc).isoformat(), 'Collection complete', flush=True)
            wait = interval
        except Exception as error:
            # Do not log provider URLs: they contain the odds API credential.
            print('Collection failed:', type(error).__name__, 'retrying in 5 minutes', flush=True)
            wait = max(interval, 300)
        time.sleep(wait)

if __name__ == '__main__':
    main()
