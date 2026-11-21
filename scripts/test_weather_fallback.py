import datetime as dt,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.refresh_stadium_weather import run,UTC

class WeatherFallbackTests(unittest.TestCase):
 def collect(self,hours):
  kickoff=dt.datetime.now(UTC)+dt.timedelta(hours=hours)
  csv='season,game_type,week,game_id,home_team,away_team,stadium,kickoff\n'+f'{kickoff.year},REG,11,g,BUF,MIA,Test Stadium,{kickoff.isoformat()}\n'
  def request(url,*args,**kwargs):
   if 'open-meteo' in url:raise RuntimeError('429')
   return {'success':True,'response':[{'periods':[{'dateTimeISO':kickoff.isoformat(),'tempC':8,'windSpeedKPH':20,'windGustKPH':30,'precipMM':1,'pop':70,'windDirDEG':270}]}]}
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'data').mkdir();(root/'data/stadium-venues.json').write_text(json.dumps({'stadiums':{'Test Stadium':{'latitude':42.7,'longitude':-78.8,'roofType':'outdoor'}}}))
   with patch('scripts.refresh_stadium_weather.ROOT',root),patch('scripts.refresh_stadium_weather.urlopen',return_value=io.BytesIO(csv.encode())),patch('scripts.refresh_stadium_weather.request_json',side_effect=request) as requests,patch('intelligence.providers.xweather_credentials',return_value=('test-id','test-secret')):
    result=run(resolve_venues=False)
   return result,requests.call_count
 def test_public_rate_limit_uses_authenticated_forecast_for_tomorrow(self):
  result,calls=self.collect(24);game=result['games'][0]
  self.assertEqual(game['status'],'ok');self.assertEqual(game['provider'],'Xweather');self.assertEqual(game['kickoffForecast']['temperatureC'],8);self.assertEqual(game['kickoffForecast']['windKph'],20);self.assertEqual(calls,2)
 def test_farther_games_do_not_spend_authenticated_fallback_requests(self):
  result,calls=self.collect(72);self.assertEqual(result['games'][0]['status'],'unavailable');self.assertEqual(calls,1)
