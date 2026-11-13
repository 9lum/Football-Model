import datetime as dt,unittest
from scripts.restore_odds_coverage import planned_requests
from scripts.odds_quota import kickoff_reserve,routine_budget
class RecoveryTests(unittest.TestCase):
 def test_current_allowance_can_restore_all_games_without_spending_kickoff_reserve(self):
  now=dt.datetime(2026,11,13,tzinfo=dt.timezone.utc);events=[{'id':str(i),'commence_time':'2026-11-15T18:00Z'} for i in range(13)]
  tasks=planned_requests(events,190,now);cost=3+sum(len(m) for e,m in tasks)
  self.assertEqual(len(tasks),26);self.assertEqual(cost,55);self.assertGreaterEqual(190-cost,kickoff_reserve(now));self.assertEqual(routine_budget(190,999,now),78)
 def test_low_allowance_stops_before_the_reserve_and_prioritizes_td_coverage(self):
  now=dt.datetime(2026,11,13,tzinfo=dt.timezone.utc);events=[{'id':str(i),'commence_time':'2026-11-15T18:00Z'} for i in range(13)]
  tasks=planned_requests(events,120,now);self.assertLessEqual(3+sum(len(m) for e,m in tasks),8);self.assertTrue(all(m==['player_anytime_td'] for e,m in tasks))
 def test_recovery_merges_core_prices_and_preserves_unrequested_market_timestamps(self):
  import tempfile,json
  from pathlib import Path
  from unittest.mock import patch
  from scripts.restore_odds_coverage import run
  now=dt.datetime(2026,11,13,tzinfo=dt.timezone.utc);event={'id':'a','commence_time':'2026-11-15T18:00:00Z','home_team':'Seattle Seahawks','away_team':'Arizona Cardinals'}
  old={**event,'bookmakers':[{'key':'book','title':'Book','markets':[{'key':'player_receptions','last_update':'old','outcomes':[{'price':-110}]}]}]}
  td={**event,'bookmakers':[{'key':'book','title':'Book','markets':[{'key':'player_anytime_td','last_update':now.isoformat(),'outcomes':[{'price':150}]}]}]}
  core={**event,'bookmakers':[{'key':'book','title':'Book','markets':[{'key':'player_pass_yds','last_update':now.isoformat(),'outcomes':[{'price':-105}]}]}]}
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory);(p/'odds.json').write_text(json.dumps({'data':[old]}))
   with patch('scripts.restore_odds_coverage.fetch',side_effect=[([event],{'remaining':'190','used':'310'}),(td,{'remaining':'186','used':'314','last':'1'}),(core,{'remaining':'183','used':'317','last':'3'})]),patch('scripts.restore_odds_coverage.collect_game_odds',return_value={'quota':{'remaining':'187','used':'313','last':'3'}}):run(p,'secret',now)
   result=json.loads((p/'odds.json').read_text());markets={m['key']:m for m in result['data'][0]['bookmakers'][0]['markets']};self.assertEqual(markets['player_receptions']['last_update'],'old');self.assertEqual(markets['player_pass_yds']['last_update'],now.isoformat());self.assertEqual(result['quota']['used'],'317');self.assertNotIn('secret',(p/'odds.json').read_text())
