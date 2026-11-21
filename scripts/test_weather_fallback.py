import datetime as dt,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.refresh_stadium_weather import run,UTC

class WeatherFallbackTests(unittest.TestCase):
 def collect(self,hours):
  kickoff=dt.datetime.now(UTC)+dt.timedelta(hours=hours)
  csv='season,game_type,week,game_id,home_team,away_team,stadium,kickoff\n'+f'{kickoff.year},REG,11,g,BUF,MIA,Test Stadium,{kickoff.isoformat()}\n'
  def request(url,*args,**kwargs):
   if '/points/' in url:return {'properties':{'forecastHourly':'hourly','forecastGridData':'grid'}}
   if url=='hourly':return {'properties':{'periods':[{'startTime':kickoff.isoformat(),'temperature':8,'temperatureUnit':'C','windSpeed':'10 mph','windDirection':'W','probabilityOfPrecipitation':{'value':70}}]}}
   if url=='grid':return {'properties':{}}
   raise RuntimeError('429')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'data').mkdir();(root/'data/stadium-venues.json').write_text(json.dumps({'stadiums':{'Test Stadium':{'latitude':42.7,'longitude':-78.8,'roofType':'outdoor'}}}))
   with patch('scripts.refresh_stadium_weather.ROOT',root),patch('scripts.refresh_stadium_weather.urlopen',return_value=io.BytesIO(csv.encode())),patch('scripts.refresh_stadium_weather.request_json',side_effect=request) as requests,patch('intelligence.providers.xweather_credentials',return_value=('test-id','test-secret')):
    result=run(resolve_venues=False)
   return result,requests.call_count
 def test_tomorrow_uses_free_weather_even_when_paid_credentials_exist(self):
  result,calls=self.collect(24);game=result['games'][0]
  self.assertEqual(game['status'],'ok');self.assertEqual(game['provider'],'National Weather Service');self.assertEqual(game['kickoffForecast']['temperatureC'],8);self.assertTrue(result['freeOnly']);self.assertEqual(calls,3)
 def test_later_games_use_free_published_hourly_data(self):
  result,calls=self.collect(72);self.assertEqual(result['games'][0]['status'],'ok');self.assertEqual(calls,3)
