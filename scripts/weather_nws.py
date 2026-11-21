"""Free NOAA/NWS hourly forecasts; quantities retain published units and validity intervals."""
import datetime as dt,math,re
UTC=dt.timezone.utc
HEADERS={'User-Agent':'ProjectionsNShitWeather (https://github.com/9lum/Football-Model)','Accept':'application/geo+json'}
def finite(v):return isinstance(v,(int,float)) and math.isfinite(v)
def instant(s):return dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(UTC)
def duration(s):
 m=re.fullmatch(r'P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?',s)
 return sum(int(v or 0)*scale for v,scale in zip(m.groups(),[86400,3600,60])) if m else 0

def grid_value(grid,key,at,one_hour=False):
 field=grid.get(key,{})
 for row in field.get('values',[]):
  try:
   start,span=row['validTime'].split('/');seconds=duration(span);begin=instant(start)
   if begin<=at<begin+dt.timedelta(seconds=seconds) and (not one_hour or seconds==3600):
    value=row.get('value');return value if finite(value) else None
  except (KeyError,ValueError,TypeError):continue
 return None

def celsius(value,unit):return (value-32)*5/9 if finite(value) and unit=='F' else value if finite(value) and unit in ['C','wmoUnit:degC'] else None

def fetch_nws(point,request):
 if not (24<=point[0]<=50 and -126<=point[1]<=-66):return None
 info=request(f'https://api.weather.gov/points/{point[0]:.4f},{point[1]:.4f}',headers=HEADERS)['properties']
 payload=request(info['forecastHourly'],headers=HEADERS);props=payload['properties'];grid={}
 try:grid=request(info['forecastGridData'],headers=HEADERS).get('properties',{})
 except Exception:pass
 fields=['time','temperature_2m','apparent_temperature','relative_humidity_2m','dew_point_2m','precipitation_probability','precipitation','rain','snowfall','wind_speed_10m','wind_gusts_10m','wind_direction_10m','visibility','cloud_cover','surface_pressure','weather_code','is_day']
 hourly={k:[] for k in fields};compass=['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW']
 for p in props.get('periods',[]):
  at=instant(p['startTime']);wind=grid_value(grid,'windSpeed',at);gust=grid_value(grid,'windGust',at)
  if wind is None:
   match=re.fullmatch(r'(\d+(?:\.\d+)?) mph',p.get('windSpeed',''))
   wind=float(match[1])*1.609344 if match else None
  # NWS grid wind units are typically km/h; unknown units are left unavailable.
  if grid.get('windSpeed',{}).get('uom') not in [None,'wmoUnit:km_h-1']:wind=None
  if grid.get('windGust',{}).get('uom')!='wmoUnit:km_h-1':gust=None
  direction=p.get('windDirection');direction=compass.index(direction)*22.5 if direction in compass else None
  desc=p.get('shortForecast','').lower();code=95 if 'thunder' in desc else 71 if 'snow' in desc else 61 if 'rain' in desc or 'showers' in desc else 2 if 'partly' in desc else 3 if 'cloudy' in desc else 0 if 'sunny' in desc or 'clear' in desc else None
  qpf=grid_value(grid,'quantitativePrecipitation',at,one_hour=True)
  if grid.get('quantitativePrecipitation',{}).get('uom') not in ['wmoUnit:mm','wmoUnit:kg_m-2']:qpf=None
  values={'time':at.replace(tzinfo=None).isoformat(),'temperature_2m':celsius(p.get('temperature'),p.get('temperatureUnit')),'relative_humidity_2m':p.get('relativeHumidity',{}).get('value'),'dew_point_2m':celsius(p.get('dewpoint',{}).get('value'),p.get('dewpoint',{}).get('unitCode')),'precipitation_probability':p.get('probabilityOfPrecipitation',{}).get('value'),'precipitation':qpf,'wind_speed_10m':wind,'wind_gusts_10m':gust,'wind_direction_10m':direction,'cloud_cover':grid_value(grid,'skyCover',at),'weather_code':code,'is_day':int(p.get('isDaytime',False))}
  for key in fields:hourly[key].append(values.get(key))
 if not hourly['time']:return None
 return {'hourly':hourly,'_provider':'National Weather Service','_source':info['forecastHourly'],'_issuedAt':props.get('updateTime') or props.get('generatedAt'),'_model':'NWS hourly + published grid validity intervals','_note':'Free NOAA/NWS data. Gusts and cloud cover follow their published grid validity intervals. Multi-hour precipitation totals are not relabeled as hourly amounts. Missing quantities remain unavailable.'}
