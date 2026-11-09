"""Versioned public-source downloads. No credentials or private endpoints."""
import gzip
import hashlib
import io
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import pandas as pd

BASE = 'https://github.com/nflverse/nflverse-data/releases/download/'
TEAM_ALIASES = {'LA':'LAR','STL':'LAR','SD':'LAC','OAK':'LV','BLT':'BAL','CLV':'CLE','ARZ':'ARI','HST':'HOU','JAC':'JAX','WSH':'WAS'}
def team(x):
    return TEAM_ALIASES.get(str(x), str(x))

def get(url):
    for attempt in range(3):
        try:
            request_url=url
            if attempt and url.startswith(BASE):request_url=url+('&' if '?' in url else '?')+'refresh='+datetime.now(timezone.utc).strftime('%Y%m%d%H')+'-'+str(attempt)
            with urlopen(Request(request_url, headers={'User-Agent':'RouteEdgeResearch/0.3','Cache-Control':'no-cache'}), timeout=60) as r:
                return r.read(), {'url':url, 'retrievedAt':datetime.now(timezone.utc).isoformat(),
                                 'lastModified':r.headers.get('Last-Modified'), 'etag':r.headers.get('ETag')}
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

def csv_asset(tag, name, cache, manifest):
    try:raw, meta = get(BASE+tag+'/'+name)
    except Exception:
        if tag!='schedules' or name!='games.csv':raise
        raw,meta=get('https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv')
    meta['sha256'] = hashlib.sha256(raw).hexdigest()
    meta['bytes'] = len(raw)
    cache.mkdir(parents=True, exist_ok=True)
    (cache/name).write_bytes(raw)
    manifest.append(meta)
    if name.endswith('.gz'):
        raw = gzip.decompress(raw)
    return pd.read_csv(io.BytesIO(raw), low_memory=False)

def normalize_stats(frame,positions=None):
    d = frame.copy()
    for canonical, aliases in {'player_id':['gsis_id'], 'player_display_name':['player_name','display_name'],
                               'team':['recent_team'], 'opponent_team':['opponent'],
                               'season_type':['game_type'],'passing_interceptions':['interceptions'],'sacks_suffered':['sacks']}.items():
        if canonical not in d:
            for alias in aliases:
                if alias in d:
                    d[canonical] = d[alias]
                    break
    required = ['player_id','player_display_name','position','season','week','team','targets','receptions','receiving_yards']
    missing = set(required)-set(d)
    if missing:
        raise ValueError('Player-stat schema missing '+str(sorted(missing)))
    d = d[d.position.isin(positions or ['WR','TE','RB'])].copy()
    if 'season_type' in d:
        d = d[d.season_type.eq('REG')]
    from .profiles import COUNTERS
    for key in COUNTERS:
        if key not in d:
            d[key] = float('nan')
        d[key] = pd.to_numeric(d[key], errors='coerce')
    d['team'] = d.team.map(team)
    return d

def schedule_rows(games):
    rows = []
    for g in games.to_dict('records'):
        if str(g.get('game_type','REG')) != 'REG':
            continue
        # gametime is Eastern local time in nflverse schedules; never substitute final scores as predictors.
        stamp = pd.to_datetime(str(g['gameday'])+' '+str(g.get('gametime','13:00')), errors='coerce')
        if pd.isna(stamp):
            continue
        kickoff = stamp.tz_localize('America/New_York', ambiguous='NaT', nonexistent='shift_forward').tz_convert('UTC')
        for home in [True, False]:
            rows.append({'game_id':g['game_id'], 'season':int(g['season']), 'week':int(g['week']),
                         'team':team(g['home_team'] if home else g['away_team']),
                         'opponent_team':team(g['away_team'] if home else g['home_team']),
                         'home':int(home), 'kickoff':kickoff,
                         'points_allowed':g.get('away_score' if home else 'home_score',float('nan')),
                         'home_team':team(g['home_team']), 'away_team':team(g['away_team']),
                         'completed':pd.notna(g.get('home_score')) and pd.notna(g.get('away_score'))})
    return pd.DataFrame(rows)

def add_snap_zeros(stats, snaps, players):
    """Retain active zero-target games; do not turn unknown/DNP games into zeroes."""
    s = snaps.copy()
    required = {'pfr_player_id','offense_snaps','season','week','team','position'}
    if not required.issubset(s):
        raise ValueError('Snap-count schema changed')
    pfr = 'pfr_id' if 'pfr_id' in players else 'pfr_player_id'
    gsis = 'gsis_id' if 'gsis_id' in players else 'player_id'
    mapping = players[[pfr,gsis]].dropna().drop_duplicates()
    # Ambiguous crosswalks fail closed instead of matching abbreviated names.
    mapping = mapping[~mapping[pfr].duplicated(keep=False)]
    s = s.merge(mapping, left_on='pfr_player_id', right_on=pfr, how='left')
    eligible = s.position.isin(['QB','WR','TE','RB']) & (s.offense_snaps > 0)
    unmapped = int((eligible & s[gsis].isna()).sum())
    s = s[eligible & s[gsis].notna()].copy()
    if 'game_type' in s:
        s = s[s.game_type.eq('REG')]
    s['player_id'] = s[gsis]
    s['team'] = s.team.map(team)
    s['player_display_name'] = s['player']
    keys = ['player_id','season','week','team']
    # Snap counts can arrive before player stats. Never label an unpublished entire game as all zeroes.
    published = stats[['season','week','team']].drop_duplicates()
    before = len(s)
    s = s.merge(published,on=['season','week','team'],how='inner',validate='many_to_one')
    skipped_unpublished = before-len(s)
    s = s.drop_duplicates(keys)
    merged = stats.merge(s[keys+['offense_snaps','offense_pct']], on=keys, how='outer', indicator=True)
    for field in ['player_display_name','position']:
        lookup = s.set_index(keys)[field]
        missing = merged[field].isna()
        merged.loc[missing,field] = [lookup.get(tuple(v)) for v in merged.loc[missing,keys].to_numpy()]
    new = merged['_merge'].eq('right_only')
    from .profiles import COUNTERS
    for field in [k for k in COUNTERS if k in merged]:
        merged.loc[new,field] = 0
    return merged.drop(columns='_merge'), {'addedZeroTargetGames':int(new.sum()),'unmappedSkillPositionSnapRows':unmapped,'snapRowsWaitingForGameStats':skipped_unpublished}

def sumer_snapshot(html, url, observed_at=None):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(' ', strip=True)
    match = re.search(r'(?:Last\s+)?Updated\s+(\d{2}-\d{2}-\d{4})\s+(\d{1,2}:\d{2})\s+(AM|PM)', text, re.I)
    if not match:
        raise ValueError('SumerSports update timestamp missing')
    asof = pd.to_datetime(' '.join(match.groups()), format='%m-%d-%Y %I:%M %p').tz_localize('America/New_York').tz_convert('UTC')
    table = next((t for t in soup.select('table') if 'Routes Run' in t.get_text() and 'ADoT' in t.get_text()), None)
    if table is None:
        raise ValueError('No public route table; JS-rendered or schema changed')
    headers = [re.sub(r'\s+',' ',h.get_text(' ',strip=True)) for h in table.select('thead th')]
    if not headers:
        headers = [h.get_text(' ',strip=True) for h in table.select('tr')[0].select('th,td')]
    required = {'Routes Run','ADoT','Targets/Route Run','Receptions','YAC'}
    if not required.issubset(headers):
        raise ValueError('SumerSports route columns missing')
    records=[]
    for tr in table.select('tbody tr'):
        cells=tr.select('td')
        if len(cells)!=len(headers):
            continue
        a=tr.select_one('a[href*="/players/"]')
        if not a:
            continue
        record=dict(zip(headers,[c.get_text(' ',strip=True) for c in cells]))
        record.update({'profileUrl':a['href'], 'label':a.get_text(' ',strip=True)})
        for key in required|{'Catch %','Target Share','YPRR','Rec. Yards'}:
            if key in record:
                value=record[key].replace(',','').replace('%','').strip()
                record[key]=float(value) if value and value not in ['—','-'] else None
        records.append(record)
    if not records:
        raise ValueError('Empty SumerSports route table')
    return {'source':url,'asOf':asof.isoformat(),'observedAt':observed_at or datetime.now(timezone.utc).isoformat(),
            'scope':'Current public season aggregates; not valid for earlier-week backtesting','players':records}

def collect(start, season, directory, include_sumer=True):
    cache=directory/'raw'; manifest=[]
    games=csv_asset('schedules','games.csv',cache,manifest)
    players=csv_asset('players','players.csv',cache,manifest)
    stats=[]; snaps=[]
    for year in range(start,season+1):
        stats.append(normalize_stats(csv_asset('stats_player',f'stats_player_week_{year}.csv.gz',cache,manifest),positions=['QB','WR','TE','RB']))
        snaps.append(csv_asset('snap_counts',f'snap_counts_{year}.csv.gz',cache,manifest))
    stats, quality=add_snap_zeros(pd.concat(stats,ignore_index=True),pd.concat(snaps,ignore_index=True),players)
    optional={}
    if include_sumer:
        for position in ['wide-receiver','tight-end']:
            url='https://sumersports.com/players/'+position+'/'
            try:
                raw,meta=get(url)
                snapshot=sumer_snapshot(raw.decode(),url)
                optional[position]=snapshot
                manifest.append(meta)
            except Exception as e:
                optional[position]={'error':type(e).__name__,'status':'unavailable; no invented route values'}
    directory.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    (directory/f'sumer-{stamp}.json').write_text(json.dumps(optional,indent=2))
    (directory/'sources.json').write_text(json.dumps({'sources':manifest,'quality':quality},indent=2))
    return stats,schedule_rows(games),optional,manifest,quality
