import unittest
from scripts.model_performance import build_performance
from scripts.performance_boxscore import player_stats,touchdown_order
class PerformanceTests(unittest.TestCase):
 def build(self,published=None,oos=None,history=None,td=None,results=None,previous=None):return build_performance(previous or {},published or {},oos or [],{'players':[]},history or {},td or [],{'results':results or []},{},'2026-11-09T04:00Z')
 def test_published_and_walk_forward_stay_separate_and_duplicate_inputs_do_not_duplicate_rows(self):
  row={'id':'g|p|m','gameId':'2026_09_CIN_ATL','season':2026,'week':9,'playerId':'p','player':'Player One','market':'player_receptions','target':'receptions','team':'CIN','kickoff':'2026-11-08T18:00Z','issuedAt':'2026-11-07T18:00Z','projected':4,'actual':5,'status':'scored'}
  oos={'game_id':row['gameId'],'player_id':'p','week':9,'receptions':{'mean':3,'actual':5,'baseline':2,'p10':1,'p90':6}}
  value=self.build({'rows':[row,row]},[oos,oos]);self.assertEqual(len(value['forecasts']),2);self.assertEqual({r['scope'] for r in value['forecasts']},{'published','walk_forward'})
  row['projected']=9;updated=self.build({'rows':[row]},previous=value);self.assertEqual(next(r for r in updated['forecasts'] if r['scope']=='published')['projected'],4)
 def test_post_kickoff_forecasts_excluded_and_missing_actuals_not_zero_filled(self):
  row={'id':'x','gameId':'2026_09_CIN_ATL','market':'player_receptions','kickoff':'2026-11-08T18:00Z','issuedAt':'2026-11-08T19:00Z'}
  self.assertEqual(self.build({'rows':[row]})['forecasts'],[])
 def test_boxscore_extracts_explicit_attempts_completions_and_interceptions(self):
  payload={'boxscore':{'players':[{'team':{'displayName':'Team'},'statistics':[{'name':'passing','keys':['completions/passingAttempts','passingYards','passingTouchdowns','interceptions'],'athletes':[{'athlete':{'id':'1','displayName':'QB'},'stats':['20/30','250','2','1']}]}]}]}}
  stats=player_stats(payload)[0]['stats'];self.assertEqual(stats['attempts'],30);self.assertEqual(stats['completions'],20);self.assertEqual(stats['passing_interceptions'],1);self.assertNotIn('receiving_yards',stats)
 def test_unresolved_touchdown_order_is_not_guessed(self):
  self.assertFalse(touchdown_order({'scoringPlays':[{'scoringType':{'name':'touchdown'},'text':'Unknown Player 5 Yd Rush','team':{'displayName':'Team'}}]})['complete'])
 def test_combined_totals_require_matching_components_and_do_not_add_intervals(self):
  oos={'game_id':'2026_01_CIN_ATL','player_id':'p','week':1,'rushing_yards':{'mean':50,'actual':40,'baseline':45,'p10':0,'p90':100},'receiving_yards':{'mean':20,'actual':30,'baseline':15,'p10':0,'p90':50}}
  result=self.build(oos=[oos]);combined=next(r for r in result['forecasts'] if r['market']=='combined_rush_rec_yards');self.assertEqual(combined['projected'],70);self.assertEqual(combined['actual'],70);self.assertEqual(combined['baseline'],60);self.assertIsNone(combined['p90'])
