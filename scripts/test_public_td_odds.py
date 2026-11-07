import datetime as dt,unittest
from scripts.refresh_public_td_odds import parse
class PublicTdTests(unittest.TestCase):
 def test_exact_match_and_two_plus_stays_distinct_from_anytime(self):
  now=dt.datetime(2026,11,7,tzinfo=dt.timezone.utc);f={'gameId':'2026_09_NYJ_KC','name':'Test Player','homeTeam':'KC','awayTeam':'NYJ','kickoff':'2026-11-08T18:00:00Z'}
  row='<tr><td>NY Jets @ KC Chiefs</td><td>11/8, 01:00PM</td><td>2+ TDs</td><td>Test Player</td><td><a href="https://sportsbook.draftkings.com/event/123">+220</a></td></tr>'
  result=parse(row,{'forecasts':[f]},now);m=result[0]['bookmakers'][0]['markets'][0];self.assertEqual(m['key'],'player_tds_over');self.assertEqual(m['outcomes'][0]['point'],1.5);self.assertIsNone(m['last_update']);self.assertEqual(m['sourceKind'],'public_web')
  self.assertFalse(parse(row.replace('NY Jets','NY Giants'),{'forecasts':[f]},now));self.assertFalse(parse(row.replace('11/8','11/15'),{'forecasts':[f]},now));self.assertFalse(parse(row,{'forecasts':[f,f]},now))
