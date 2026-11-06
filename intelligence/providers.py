"""Documented provider adapters. Never put request URLs or credential values in logs."""
import datetime as dt
import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError

UTC=dt.timezone.utc
class ProviderError(Exception):
    def __init__(self,code):self.code=code

def request_json(url,params=None,headers=None):
    url=url+('?' + urlencode(params,doseq=True) if params else '')
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={'User-Agent':'Projections-n-Shit/1.0',**(headers or {})}),timeout=30) as response:return json.load(response)
        except HTTPError as error:
            if error.code in [429,500,502,503] and attempt<2:time.sleep(2**attempt);continue
            raise ProviderError(error.code) from None
        except Exception:
            if attempt<2:time.sleep(2**attempt);continue
            raise ProviderError('network_or_schema') from None

def bdl_pages(endpoint,key,params=None,max_pages=6):
    result=[];cursor=None
    for _ in range(max_pages):
        query={'per_page':100,**(params or {})}
        if cursor:query['cursor']=cursor
        payload=request_json('https://api.balldontlie.io/nfl/v1/'+endpoint,query,{'Authorization':key})
        if not isinstance(payload.get('data'),list):raise ProviderError('schema')
        result.extend(payload['data']);cursor=payload.get('meta',{}).get('next_cursor')
        if not cursor:return result,True
        time.sleep(1)
    return result,False

def collect_bdl(season,week):
    key=os.environ.get('BALLDLIE_API_KEY') or os.environ.get('BALLDONTLIE_API_KEY')
    state={'provider':'BALLDONTLIE','observedAt':dt.datetime.now(UTC).isoformat(),'datasets':{},'errors':[]}
    if not key:return {**state,'status':'missing_secret','requiredSecret':'BALLDLIE_API_KEY (or BALLDONTLIE_API_KEY)'}
    specs={'teams':({},1),'players':({},6),'games':({'seasons[]':season,'weeks[]':week},2),'player_injuries':({},6),
           'stats':({'seasons[]':season},4),**{'advanced_stats/'+kind:({'season':season,'week':0},4) for kind in ['passing','rushing','receiving']}}
    for endpoint,(params,pages) in specs.items():
        try:
            rows,complete=bdl_pages(endpoint,key,params,pages);state['datasets'][endpoint]={'status':'ok','rows':rows,'count':len(rows),'paginationComplete':complete}
        except ProviderError as error:
            state['datasets'][endpoint]={'status':'unavailable','code':error.code,'rows':[],'count':0};state['errors'].append({'endpoint':endpoint,'code':error.code})
            if error.code==429:break
        time.sleep(1)
    ok=sum(d['status']=='ok' for d in state['datasets'].values());state['status']='ok' if ok==len(specs) else 'partial' if ok else 'unavailable'
    return state

# Home stadium coordinates; international games override by schedule stadium name.
LOCATIONS={'ARI':(33.5276,-112.2626),'ATL':(33.7554,-84.4008),'BAL':(39.278,-76.6227),'BUF':(42.7738,-78.787),'CAR':(35.2258,-80.8528),'CHI':(41.8623,-87.6167),'CIN':(39.0954,-84.516),'CLE':(41.5061,-81.6995),'DAL':(32.7473,-97.0945),'DEN':(39.7439,-105.0201),'DET':(42.34,-83.0456),'GB':(44.5013,-88.0622),'HOU':(29.6847,-95.4107),'IND':(39.7601,-86.1639),'JAX':(30.324,-81.6373),'KC':(39.0489,-94.4839),'LAC':(33.9535,-118.3392),'LAR':(33.9535,-118.3392),'LV':(36.0908,-115.183),'MIA':(25.958,-80.2389),'MIN':(44.9736,-93.2575),'NE':(42.0909,-71.2643),'NO':(29.9511,-90.0812),'NYG':(40.8135,-74.0745),'NYJ':(40.8135,-74.0745),'PHI':(39.9008,-75.1675),'PIT':(40.4468,-80.0158),'SEA':(47.5952,-122.3316),'SF':(37.403,-121.97),'TB':(27.9759,-82.5033),'TEN':(36.1665,-86.7713),'WAS':(38.9077,-76.8645)}
INTERNATIONAL={'wembley':(51.556, -.2796),'tottenham':(51.6043,-.0664),'berlin':(52.5147,13.2395),'munich':(48.2188,11.6247),'madrid':(40.4531,-3.6883),'dublin':(53.3352,-6.2285),'são paulo':(-23.5453,-46.4739),'sao paulo':(-23.5453,-46.4739),'melbourne':(-37.82,144.983),'mexico':(19.3029,-99.1505)}

def venue(game):
    stadium=str(game.get('stadium','')).lower();neutral=str(game.get('location','Home')).lower()=='neutral'
    for word,coords in INTERNATIONAL.items():
        if word in stadium:return coords
    if neutral:return None
    return LOCATIONS.get({'LA':'LAR','WSH':'WAS','JAC':'JAX'}.get(game.get('home_team'),game.get('home_team')))

def xweather_credentials():
    key=os.environ.get('XWEATHER_API_KEY','').strip();client=os.environ.get('XWEATHER_CLIENT_ID','').strip()
    if key.startswith('{'):
        try:
            obj=json.loads(key);client=client or obj.get('client_id','');key=obj.get('client_secret','')
        except ValueError:return '', ''
    return client,key

def collect_weather(games,now=None):
    now=now or dt.datetime.now(UTC);client,key=xweather_credentials();rows=[];errors=[];used=set();xweather_rejected=False
    for game in games:
        if game['game_id'] in used:continue
        used.add(game['game_id']);kickoff=dt.datetime.fromisoformat(game['kickoff'].replace('Z','+00:00'))
        if not now<kickoff<now+dt.timedelta(days=8):continue
        coords=venue(game);entry={'gameId':game['game_id'],'kickoff':game['kickoff'],'stadium':game.get('stadium'),'roof':game.get('roof'),'observedAt':now.isoformat(),'status':'unavailable','appliedToModel':False}
        if not coords:entry['reason']='Unresolved neutral venue';rows.append(entry);continue
        entry['latitude'],entry['longitude']=coords
        if client and key and not xweather_rejected:
            try:
                payload=request_json(f'https://data.api.xweather.com/forecasts/{coords[0]},{coords[1]}',{'client_id':client,'client_secret':key,'filter':'1hr','from':kickoff.isoformat(),'to':(kickoff+dt.timedelta(hours=3)).isoformat(),'limit':4})
                if not payload.get('success'):raise ProviderError('provider_rejected')
                response=payload.get('response',[]);periods=response[0].get('periods',[]) if response else []
                if not periods:raise ProviderError('forecast_unavailable')
                period=min(periods,key=lambda p:abs(dt.datetime.fromisoformat(p['dateTimeISO'].replace('Z','+00:00')).timestamp()-kickoff.timestamp()))
                entry.update(provider='Xweather',status='ok',forecastTime=period.get('dateTimeISO'),temperatureC=period.get('avgTempC',period.get('tempC',period.get('maxTempC'))),windKph=period.get('windSpeedKPH',period.get('windSpeedAvgKPH',period.get('windSpeedMaxKPH'))),precipitationMm=period.get('precipMM'),precipitationProbability=period.get('pop'))
            except ProviderError as error:
                errors.append({'provider':'Xweather','gameId':entry['gameId'],'code':error.code})
                if error.code in [401,403]:xweather_rejected=True
        if entry['status']!='ok':
            try:
                payload=request_json('https://api.open-meteo.com/v1/forecast',{'latitude':coords[0],'longitude':coords[1],'hourly':'temperature_2m,precipitation,precipitation_probability,wind_speed_10m','forecast_days':8,'timezone':'UTC'})
                hourly=payload['hourly'];times=[dt.datetime.fromisoformat(t).replace(tzinfo=UTC) for t in hourly['time']];index=min(range(len(times)),key=lambda i:abs((times[i]-kickoff).total_seconds()))
                if abs((times[index]-kickoff).total_seconds())>5400:raise ProviderError('outside_forecast_horizon')
                entry.update(provider='Open-Meteo',status='ok',forecastTime=times[index].isoformat(),temperatureC=hourly['temperature_2m'][index],windKph=hourly['wind_speed_10m'][index],precipitationMm=hourly['precipitation'][index],precipitationProbability=hourly['precipitation_probability'][index])
            except (ProviderError,KeyError,ValueError) as error:entry['reason']=getattr(error,'code','schema')
        # Weather is context until an out-of-sample weather model is fitted; never fabricate yardage penalties.
        entry['exposure']='indoor' if str(entry.get('roof','')).lower() in ['dome','closed'] else 'roof_pending' if str(entry.get('roof','')).lower() in ['retractable','retractable roof'] else 'outdoor_or_unknown'
        rows.append(entry)
    return {'generatedAt':now.isoformat(),'xweatherStatus':'authentication_rejected' if xweather_rejected else 'configured' if client and key else 'missing_client_id' if key else 'missing_secret','errors':errors,'games':rows,'scope':'Kickoff forecasts; contextual only, not a validated causal yardage adjustment. Open-Meteo public API fallback is for noncommercial use subject to its terms.'}
