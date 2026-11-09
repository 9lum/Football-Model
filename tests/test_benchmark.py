import unittest
from datetime import datetime
from edge.benchmark import attach_benchmarks
class BenchmarkTests(unittest.TestCase):
 def test_capture_is_pregame_unique_and_frozen(self):
  row={'id':'g','gameId':'2026_09_CIN_ATL','player':'Player One','market':'player_receptions','kickoff':'2026-11-08T18:00Z','issuedAt':'2026-11-07T00:00Z'}
  odds={'generatedAt':'2026-11-08T16:00Z','data':[{'home_team':'Atlanta Falcons','away_team':'Cincinnati Bengals','commence_time':row['kickoff'],'bookmakers':[{'key':'draftkings','title':'DraftKings','markets':[{'key':'player_receptions','outcomes':[{'description':'Player One','name':'Over','point':4.5}]}]}]}]}
  captured=attach_benchmarks([row],odds,datetime.fromisoformat('2026-11-08T17:00+00:00'));self.assertEqual(captured[0]['benchmark']['line'],4.5)
  odds['data'][0]['bookmakers'][0]['markets'][0]['outcomes'][0]['point']=6.5
  self.assertEqual(attach_benchmarks(captured,odds,datetime.fromisoformat('2026-11-08T17:10+00:00'))[0]['benchmark']['line'],4.5)
  self.assertNotIn('benchmark',attach_benchmarks([row],odds,datetime.fromisoformat('2026-11-08T19:00+00:00'))[0])
