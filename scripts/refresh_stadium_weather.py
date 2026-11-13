"""Public Open-Meteo stadium forecasts. Weather context never invents stat adjustments."""
import csv
import datetime as dt
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen
from zoneinfo import ZoneInfo
from intelligence.providers import request_json,LOCATIONS,INTERNATIONAL
UTC=dt.timezone.utc
ROOT=Path(__file__).resolve().parents[1]
FIELDS={'is_day':'isDay','temperature_2m':'temperatureC','apparent_temperature':'feelsLikeC','relative_humidity_2m':'humidityPct','dew_point_2m':'dewPointC','precipitation_probability':'precipitationProbability','precipitation':'precipitationMm','rain':'rainMm','snowfall':'snowfallCm','wind_speed_10m':'windKph','wind_gusts_10m':'gustKph','wind_direction_10m':'windDirection','visibility':'visibilityM','cloud_cover':'cloudPct','surface_pressure':'pressureHpa','weather_code':'weatherCode'}
ALIASES={'LA':'LAR','WSH':'WAS','JAC':'JAX'}
FIXED={'DET','MIN','NO','LV'}
RETRACTABLE={'ARI','ATL','DAL','HOU','IND'}
def location(game):
    name=str(game.get('stadium','')).lower();home=ALIASES.get(game['home_team'],game['home_team'])
    international={**INTERNATIONAL,'banorte':(19.3029,-99.1505),'azteca':(19.3029,-99.1505),'bernabeu':(40.4531,-3.6883),'bernabéu':(40.4531,-3.6883),'olympiastadion':(52.5147,13.2395),'croke park':(53.3607,-6.2513),'maracan':(-22.9121,-43.2302)}
    for word,coords in international.items():
        if word in name:return coords,'retractable' if any(s in name for s in ['bernabeu','bernabéu']) else 'outdoor'
    if str(game.get('location','')).lower()=='neutral':return None,'unknown'
    roof='indoor' if home in FIXED else 'retractable' if home in RETRACTABLE else 'covered-open' if home in ['LAR','LAC'] else 'outdoor'
    return LOCATIONS.get(home),roof

def kickoff_of(game):
    if game.get('kickoff'):return dt.datetime.fromisoformat(game['kickoff'].replace('Z','+00:00')).astimezone(UTC)
    if not game.get('gameday') or not game.get('gametime'):return None
    return dt.datetime.fromisoformat(game['gameday']+'T'+game['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(UTC)

def forecast_hours(payload,kickoff):
    hourly=payload.get('hourly',{});times=hourly.get('time',[]);rows=[]
    for i,t in enumerate(times):
        stamp=dt.datetime.fromisoformat(t).replace(tzinfo=UTC)
        if kickoff-dt.timedelta(hours=2)<=stamp<=kickoff+dt.timedelta(hours=4):
            row={'time':stamp.isoformat()}
            for field,label in FIELDS.items():
                values=hourly.get(field,[]);row[label]=values[i] if i<len(values) else None
            rows.append(row)
    if not rows or min(abs((dt.datetime.fromisoformat(r['time'])-kickoff).total_seconds()) for r in rows)>1800:return []
    return rows

def xweather_hours(payload,kickoff):
    if not payload.get('success'):return []
    response=payload.get('response') or [];periods=response[0].get('periods',[]) if response else [];rows=[]
    fields={'tempC':'temperatureC','feelslikeC':'feelsLikeC','humidity':'humidityPct','dewpointC':'dewPointC','precipMM':'precipitationMm','pop':'precipitationProbability','snowCM':'snowfallCm','windSpeedKPH':'windKph','windGustKPH':'gustKph','windDirDEG':'windDirection','sky':'cloudPct','pressureMB':'pressureHpa'}
    for period in periods:
        try:stamp=dt.datetime.fromisoformat(period['dateTimeISO'].replace('Z','+00:00')).astimezone(UTC)
        except (KeyError,ValueError):continue
        if not kickoff-dt.timedelta(hours=2)<=stamp<=kickoff+dt.timedelta(hours=4):continue
        row={label:None for label in FIELDS.values()};row.update(time=stamp.isoformat())
        for source,label in fields.items():row[label]=period.get(source)
        row['temperatureC']=period.get('tempC',period.get('avgTempC'))
        row['windKph']=period.get('windSpeedKPH',period.get('windSpeedAvgKPH'))
        if period.get('visibilityKM') is not None:row['visibilityM']=period['visibilityKM']*1000
        rows.append(row)
    return rows if rows and min(abs((dt.datetime.fromisoformat(r['time'])-kickoff).total_seconds()) for r in rows)<=1800 else []

def scheduled_future(game,now):
    kickoff=kickoff_of(game)
    return kickoff>now if kickoff else bool(game.get('gameday') and dt.date.fromisoformat(game['gameday'])>=now.date())

def select_season(games,now):
    future=[g for g in games if scheduled_future(g,now)]
    return min((int(g['season']) for g in future),default=None)

def venue_registry(games):
    path=ROOT/'data/stadium-venues.json'
    try:registry=json.loads(path.read_text()).get('stadiums',{})
    except (OSError,ValueError):registry={}
    for name in dict.fromkeys(g.get('stadium','') for g in games):
        if not name or name in registry:continue
        # Only new names need geocoding. One request per second respects the public service limit.
        time.sleep(1.1)
        try:
            candidates=request_json('https://nominatim.openstreetmap.org/search',{'q':name,'format':'jsonv2','limit':3},headers={'User-Agent':'ProjectionsNShitWeather/1.0 (https://github.com/9lum/Football-Model)'})
            matches=[r for r in candidates if r.get('type') in ['stadium','sports_centre'] or r.get('addresstype')=='stadium']
            if len(matches)!=1:continue
            r=matches[0];lat,lon=float(r['lat']),float(r['lon'])
            if not -90<=lat<=90 or not -180<=lon<=180:continue
            registry[name]={'latitude':lat,'longitude':lon,'roofType':'unknown','source':'https://www.openstreetmap.org/'+r['osm_type']+'/'+str(r['osm_id']),'resolution':'unique_named_stadium_geocode','resolvedAt':dt.datetime.now(UTC).isoformat()}
        except Exception:continue
    path.write_text(json.dumps({'stadiums':registry,'attribution':'New stadium coordinates: OpenStreetMap contributors, via Nominatim. Ambiguous or unresolved names remain unavailable.'},separators=(',',':')))
    return registry

def run(game_ids=None,resolve_venues=True):
    now=dt.datetime.now(UTC);season=now.year if now.month>=3 else now.year-1
    url='https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv'
    with urlopen(url,timeout=40) as response:games=list(csv.DictReader(io.StringIO(response.read().decode())))
    games=[g for g in games if g.get('game_type') in ['REG','WC','DIV','CON','SB']]
    season=select_season(games,now)
    if season is None:
        (ROOT/'data/stadium-weather.json').write_text(json.dumps({'generatedAt':now.isoformat(),'season':None,'currentWeek':None,'games':[],'status':'awaiting_schedule','reason':'No future NFL schedule has been published. Collection resumes automatically when games are scheduled.'}))
        return
    games=[g for g in games if int(g['season'])==season]
    upcoming=[g for g in games if scheduled_future(g,now)]
    current_week=min((int(g['week']) for g in upcoming),default=None)
    if current_week is None:current_week=min((int(g['week']) for g in games),default=1)
    games=[g for g in games if int(g['week'])>=current_week]
    previous={}
    try:previous={g['gameId']:g for g in json.loads((ROOT/'data/stadium-weather.json').read_text()).get('games',[])}
    except (OSError,ValueError):pass
    if game_ids is not None:games=[g for g in games if g['game_id'] in set(game_ids)]
    registry=venue_registry(games) if resolve_venues else json.loads((ROOT/'data/stadium-venues.json').read_text()).get('stadiums',{})
    def resolved(g):
        r=registry.get(g.get('stadium',''),{});return ((r['latitude'],r['longitude']),r.get('roofType','unknown')) if r else (None,'unknown')
    coords={resolved(g)[0] for g in games if kickoff_of(g) and now<kickoff_of(g)<now+dt.timedelta(days=16) and resolved(g)[0]}
    def fetch(point):
        try:return point,request_json('https://api.open-meteo.com/v1/forecast',{'latitude':point[0],'longitude':point[1],'hourly':','.join(FIELDS),'forecast_days':16,'timezone':'UTC','wind_speed_unit':'kmh','temperature_unit':'celsius','precipitation_unit':'mm'})
        except Exception as error:return point,{'error':getattr(error,'code',type(error).__name__)}
    with ThreadPoolExecutor(max_workers=4) as executor:payloads=dict(executor.map(fetch,coords))
    result=[];fallbacks={}
    for g in games:
        kickoff=kickoff_of(g);point,roof=resolved(g)
        row={'gameId':g['game_id'],'espnId':g.get('espn'),'week':int(g['week']),'season':season,'homeTeam':ALIASES.get(g['home_team'],g['home_team']),'awayTeam':ALIASES.get(g['away_team'],g['away_team']),'stadium':g.get('stadium') or 'Stadium not published','kickoff':kickoff.isoformat() if kickoff else None,'venueSource':registry.get(g.get('stadium',''),{}).get('source'),'roofType':roof,'roofConfirmed':roof=='indoor','latitude':point[0] if point else None,'longitude':point[1] if point else None,'status':'unavailable','hours':[],'appliedToModel':False}
        if not kickoff:row['reason']='Kickoff time not yet scheduled'
        elif kickoff<=now:
            old=previous.get(row['gameId'],{});row.update(hours=old.get('hours',[]),retrievedAt=old.get('retrievedAt'),status='archived',reason='Game started; retained forecast is not an observation')
        elif not point:row['reason']='Stadium coordinates unresolved or ambiguous; no home-city substitution'
        elif kickoff>=now+dt.timedelta(days=16):row.update(status='outside_horizon',reason='Hourly forecast not yet available; refreshes automatically as kickoff approaches')
        else:
            payload=payloads.get(point,{});hours=forecast_hours(payload,kickoff)
            if hours:
                at=min(hours,key=lambda r:abs((dt.datetime.fromisoformat(r['time'])-kickoff).total_seconds()))
                row.update(status='ok',hours=hours,kickoffForecast=at,retrievedAt=now.isoformat(),forecastLeadHours=round((kickoff-now).total_seconds()/3600,1),provider='Open-Meteo',model='best_match',source='https://open-meteo.com/en/docs')
            else:
                row['reason']=str(payload.get('error','Outside returned hourly horizon'))
                # Paid backup is restricted to near-kickoff venues, at most one request per venue per run.
                if now<kickoff<=now+dt.timedelta(minutes=35):
                    from intelligence.providers import xweather_credentials
                    client,key=xweather_credentials()
                    if client and key:
                        if point not in fallbacks:
                            try:fallbacks[point]=request_json(f'https://data.api.xweather.com/forecasts/{point[0]},{point[1]}',{'client_id':client,'client_secret':key,'filter':'1hr','from':(kickoff-dt.timedelta(hours=2)).isoformat(),'to':(kickoff+dt.timedelta(hours=4)).isoformat(),'limit':8})
                            except Exception:fallbacks[point]={}
                        backup=xweather_hours(fallbacks[point],kickoff)
                        if backup:
                            at=min(backup,key=lambda h:abs((dt.datetime.fromisoformat(h['time'])-kickoff).total_seconds()))
                            row.update(status='ok',hours=backup,kickoffForecast=at,retrievedAt=dt.datetime.now(UTC).isoformat(),provider='Xweather',model='provider hourly forecast',source='https://www.xweather.com/docs/weather-api/endpoints/forecasts',reason=None)
        result.append(row)
    if game_ids is not None:result=[g for gid,g in previous.items() if g.get('season')==season and gid not in {r['gameId'] for r in result}]+result
    data={'generatedAt':now.isoformat(),'season':season,'currentWeek':current_week,'games':result,'source':url,'provider':'Open-Meteo','methodology':'Best-match hourly outdoor forecasts at stadium coordinates. Retrieval time is not model issuance time. Hourly rain/snow amounts cover the preceding hour. No calibrated yardage adjustment is applied. Retractable roof status requires confirmation.','attribution':'Weather data by Open-Meteo (CC BY 4.0). Public endpoint is subject to noncommercial usage limits and terms.'}
    target=ROOT/'data/stadium-weather.json';temporary=target.with_suffix('.json.tmp');temporary.write_text(json.dumps(data,separators=(',',':'),allow_nan=False));temporary.replace(target);print(json.dumps({'games':len(result),'forecastGames':sum(r['status']=='ok' for r in result),'stadiumRequests':len(coords)}));return data
if __name__=='__main__':run()
