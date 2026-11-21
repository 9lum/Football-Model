import datetime as dt,io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.weather_nws import fetch_nws,grid_value,UTC

class NWSWeatherTests(unittest.TestCase):
 def test_units_gusts_and_multi_hour_rain_are_not_confused(self):
  at=dt.datetime(2026,11,22,18,tzinfo=UTC)
  def req(url,**kwargs):
   if '/points/' in url:return {'properties':{'forecastHourly':'hourly','forecastGridData':'grid'}}
   if url=='hourly':return {'properties':{'periods':[{'startTime':at.isoformat(),'temperature':50,'temperatureUnit':'F','windSpeed':'10 mph','windDirection':'SW','probabilityOfPrecipitation':{'value':70},'shortForecast':'Chance Rain','isDaytime':True}]}}
   return {'properties':{'windGust':{'uom':'wmoUnit:km_h-1','values':[{'validTime':at.isoformat()+'/PT6H','value':30}]},'quantitativePrecipitation':{'uom':'wmoUnit:mm','values':[{'validTime':at.isoformat()+'/PT6H','value':6}]}}}
  h=fetch_nws((42.7,-78.8),req)['hourly']
  self.assertEqual(h['temperature_2m'],[10]);self.assertAlmostEqual(h['wind_speed_10m'][0],16.09344);self.assertEqual(h['wind_gusts_10m'],[30]);self.assertEqual(h['wind_direction_10m'],[225]);self.assertEqual(h['precipitation'],[None]);self.assertEqual(h['precipitation_probability'],[70])
 def test_international_stadium_does_not_query_nws(self):
  with patch('scripts.weather_nws.instant') as unused:self.assertIsNone(fetch_nws((51.5,-.2),lambda *a,**k:self.fail('Unexpected request')))
