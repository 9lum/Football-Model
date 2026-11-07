"""Public Open-Meteo stadium forecasts. Weather context never invents stat adjustments."""
import csv
import datetime as dt
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen
from zoneinfo import ZoneInfo
from intelligence.providers import request_json,LOCATIONS,INTERNATIONAL
UTC=dt.timezone.utc
ROOT=Path(__file__).resolve().parents[1]
FIELDS={'temperature_2m':'temperatureC','apparent_temperature':'feelsLikeC','relative_humidity_2m':'humidityPct','dew_point_2m':'dewPointC','precipitation_probability':'precipitationProbability','precipitation':'precipitationMm','rain':'rainMm','snowfall':'snowfallCm','wind_speed_10m':'windKph','wind_gusts_10m':'gustKph','wind_direction_10m':'windDirection','visibility':'visibilityM','cloud_cover':'cloudPct','surface_pressure':'pressureHpa','weather_code':'weatherCode'}
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

def run():
    now=dt.datetime.now(UTC);season=now.year if now.month>=3 else now.year-1
    url='https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv'
    with urlopen(url,timeout=40) as response:games=list(csv.DictReader(io.StringIO(response.read().decode())))
    games=[g for g in games if str(g.get('season'))==str(season) and g.get('game_type') in ['REG','WC','DIV','CON','SB']]
    upcoming=[g for g in games if kickoff_of(g) and kickoff_of(g)>now]
    current_week=min((int(g['week']) for g in upcoming),default=None)
    if current_week is None:raise RuntimeError('No future season schedule available; preserving previous snapshot')
    games=[g for g in games if int(g['week'])>=current_week]
    previous={}
    try:previous={g['gameId']:g for g in json.loads((ROOT/'data/stadium-weather.json').read_text()).get('games',[])}
    except (OSError,ValueError):pass
    coords={location(g)[0] for g in games if kickoff_of(g) and now<kickoff_of(g)<now+dt.timedelta(days=16) and location(g)[0]}
    def fetch(point):
        try:return point,request_json('https://api.open-meteo.com/v1/forecast',{'latitude':point[0],'longitude':point[1],'hourly':','.join(FIELDS),'forecast_days':16,'timezone':'UTC','wind_speed_unit':'kmh','temperature_unit':'celsius','precipitation_unit':'mm'})
        except Exception as error:return point,{'error':getattr(error,'code',type(error).__name__)}
    with ThreadPoolExecutor(max_workers=4) as executor:payloads=dict(executor.map(fetch,coords))
    result=[]
    for g in games:
        kickoff=kickoff_of(g);point,roof=location(g)
        row={'gameId':g['game_id'],'espnId':g.get('espn'),'week':int(g['week']),'season':season,'homeTeam':ALIASES.get(g['home_team'],g['home_team']),'awayTeam':ALIASES.get(g['away_team'],g['away_team']),'stadium':g.get('stadium') or 'Stadium not published','kickoff':kickoff.isoformat() if kickoff else None,'roofType':roof,'roofConfirmed':roof=='indoor','latitude':point[0] if point else None,'longitude':point[1] if point else None,'status':'unavailable','hours':[],'appliedToModel':False}
        if not kickoff:row['reason']='Kickoff time not yet scheduled'
        elif kickoff<=now:
            old=previous.get(row['gameId'],{});row.update(hours=old.get('hours',[]),retrievedAt=old.get('retrievedAt'),status='archived',reason='Game started; retained forecast is not an observation')
        elif not point:row['reason']='Neutral stadium coordinates unresolved'
        elif kickoff>=now+dt.timedelta(days=16):row.update(status='outside_horizon',reason='Hourly forecast not yet available; refreshes automatically as kickoff approaches')
        else:
            payload=payloads.get(point,{});hours=forecast_hours(payload,kickoff)
            if hours:
                at=min(hours,key=lambda r:abs((dt.datetime.fromisoformat(r['time'])-kickoff).total_seconds()))
                row.update(status='ok',hours=hours,kickoffForecast=at,retrievedAt=now.isoformat(),forecastLeadHours=round((kickoff-now).total_seconds()/3600,1),provider='Open-Meteo',model='best_match',source='https://open-meteo.com/en/docs')
            else:row['reason']=str(payload.get('error','Outside returned hourly horizon'))
        result.append(row)
    data={'generatedAt':now.isoformat(),'season':season,'currentWeek':current_week,'games':result,'source':url,'provider':'Open-Meteo','methodology':'Best-match hourly outdoor forecasts at stadium coordinates. Retrieval time is not model issuance time. Hourly rain/snow amounts cover the preceding hour. No calibrated yardage adjustment is applied. Retractable roof status requires confirmation.','attribution':'Weather data by Open-Meteo (CC BY 4.0). Public endpoint is subject to noncommercial usage limits and terms.'}
    (ROOT/'data/stadium-weather.json').write_text(json.dumps(data,separators=(',',':'),allow_nan=False));print(json.dumps({'games':len(result),'forecastGames':sum(r['status']=='ok' for r in result),'stadiumRequests':len(coords)}))
if __name__=='__main__':run()
