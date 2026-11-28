import datetime as dt,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.odds_quota import observe_quota,routine_budget,kickoff_reserve
from scripts.kickoff_refresh import final_market_plan
UTC=dt.timezone.utc
class MonthlyQuotaTests(unittest.TestCase):
 def test_500_credits_cover_a_full_72_game_cycle_without_early_exhaustion(self):
  remaining=500
  for future in range(72,0,-1):
   markets=final_market_plan(remaining,1,{'remainingGames':future})
   self.assertTrue(set(['player_pass_yds','player_rush_yds','player_reception_yds','player_anytime_td']).issubset(markets))
   self.assertLessEqual(len(markets),remaining);remaining-=len(markets)
   if future>1:self.assertGreater(remaining,0)
 def test_large_overrides_cannot_bypass_monthly_preview_cap(self):
  policy={'remainingGames':72};now=dt.datetime(2026,12,1,tzinfo=UTC)
  self.assertEqual(routine_budget(500,999999,now,policy),0)
  self.assertLessEqual(routine_budget(5000,999999,now,policy),30)
  self.assertEqual(routine_budget(0,999999,now,policy),0)
 def test_reported_replenishment_restarts_estimated_cycle_without_replacing_key(self):
  with tempfile.TemporaryDirectory() as d:
   now=dt.datetime(2026,11,28,tzinfo=UTC)
   observe_quota(d,{'remaining':'0','used':'500'},now)
   renewal=observe_quota(d,{'remaining':'500','used':'0'},now+dt.timedelta(days=3))
   self.assertTrue(renewal['renewalDetected']);self.assertEqual(renewal['reportedRemaining'],500)
   self.assertIn('estimate',renewal['resetDateSource']);self.assertFalse({'apiKey','secret','token'} & renewal.keys())
 def test_complete_schedule_counts_only_games_before_configured_reset(self):
  with tempfile.TemporaryDirectory() as d:
   now=dt.datetime(2026,11,28,tzinfo=UTC);root=Path(d)
   (root/'stadium-weather.json').write_text(json.dumps({'games':[{'gameId':'one','kickoff':'2026-11-29T18:00Z'},{'gameId':'later','kickoff':'2026-12-10T18:00Z'}]}))
   with patch.dict(os.environ,{'ODDS_API_RESET_AT':'2026-12-01T00:00Z'}):state=observe_quota(root,{'remaining':'24','used':'476'},now)
   self.assertEqual(state['remainingGames'],1);self.assertEqual(state['resetDateSource'],'configured');self.assertEqual(kickoff_reserve(now,state),6)
 def test_parallel_response_order_does_not_look_like_a_monthly_reset(self):
  with tempfile.TemporaryDirectory() as d:
   now=dt.datetime(2026,11,28,tzinfo=UTC);observe_quota(d,{'remaining':'480','used':'20'},now)
   state=observe_quota(d,{'remaining':'490','used':'10'},now)
   self.assertFalse(state['renewalDetected']);self.assertEqual(state['reportedUsed'],20)

 def test_full_coverage_branch_cannot_spend_a_fresh_500_credit_month(self):
  from scripts.refresh_odds import collect
  now=dt.datetime(2026,11,28,tzinfo=UTC)
  event={'id':'e','commence_time':'2026-11-29T18:00Z','home_team':'Seattle Seahawks','away_team':'San Francisco 49ers'}
  with tempfile.TemporaryDirectory() as d,patch('scripts.refresh_odds.fetch',return_value=([event],{'remaining':'500','used':'0'})) as fetch:
   report=collect(Path(d),'never-print',now)
   self.assertEqual(fetch.call_count,1);self.assertEqual(report['creditBudget'],0);self.assertEqual(report['kickoffReservedCredits'],480)
