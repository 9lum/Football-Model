import unittest,datetime as dt
from scripts.refresh_game_weather import parse_conditions
class GameWeatherTests(unittest.TestCase):
 def fixture(self):
  return {'header':{'competitions':[{'id':'123','competitors':[{'team':{'abbreviation':'NYG'}},{'team':{'abbreviation':'WAS'}}]}]},'gameInfo':{'weather':{'temperature':48,'gust':11,'precipitation':85,'conditionId':'Cloudy'}}},{'game_id':'2026_10_WAS_NYG','espn':'123','kickoff':'2026-11-13T01:15Z','away_team':'WAS','home_team':'NYG'}
 def test_verified_report_has_units_and_no_invented_rain_or_measurement_time(self):
  p,g=self.fixture();r=parse_conditions(p,g,dt.datetime.now(dt.timezone.utc));self.assertAlmostEqual(r['temperatureC'],8.8888889);self.assertAlmostEqual(r['gustKph'],17.702784);self.assertIsNone(r['windKph']);self.assertIsNone(r['precipitationMm']);self.assertIsNone(r['precipitationProbability']);self.assertIsNone(r['observedAt']);self.assertEqual(r['kind'],'reported_game_conditions')
 def test_wrong_fixture_and_missing_weather_are_rejected(self):
  p,g=self.fixture();p['header']['competitions'][0]['id']='wrong';self.assertIsNone(parse_conditions(p,g,dt.datetime.now(dt.timezone.utc)));p,g=self.fixture();p['gameInfo']={};self.assertIsNone(parse_conditions(p,g,dt.datetime.now(dt.timezone.utc)))

 def test_in_progress_games_remain_eligible_after_upcoming_feed_drops_them(self):
  from scripts.refresh_game_weather import active_games
  now=dt.datetime(2026,11,13,2,tzinfo=dt.timezone.utc);g={'gameId':'2026_10_WAS_NYG','espnId':'123','kickoff':'2026-11-13T01:15Z'}
  self.assertEqual(active_games([], [g], [], now),[g]);self.assertEqual(active_games([],[],[g],now),[g]);self.assertEqual(active_games([],[],[g],now+dt.timedelta(days=1)),[])
