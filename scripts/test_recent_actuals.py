import unittest
from scripts.refresh_recent_actuals import extract
class RecentActualsTests(unittest.TestCase):
 def test_team_net_passing_is_not_mistaken_for_player_gross_passing(self):
  summary={'boxscore':{'players':[{'team':{'displayName':'Buffalo Bills'},'statistics':[{'name':'passing','keys':['completions/passingAttempts','passingYards','passingTouchdowns','interceptions','sacks-sackYardsLost'],'totals':['21/31','205','1','1','4-29'],'athletes':[{'athlete':{'id':'1','displayName':'QB'},'stats':['21/31','234','1','1','4-29']}]}]}]}}
  rows,checks=extract(summary);self.assertEqual(rows[0]['stats']['passing_yards'],234);self.assertEqual(rows[0]['stats']['sack_yards_lost'],-29);self.assertTrue(all(c['matches'] for c in checks));self.assertNotIn('rushing_yards',rows[0]['stats'])
 def test_mismatched_totals_are_reported_not_silently_corrected(self):
  summary={'boxscore':{'players':[{'team':{'displayName':'Minnesota Vikings'},'statistics':[{'name':'receiving','keys':['receptions','receivingYards','receivingTouchdowns','receivingTargets'],'totals':['3','50','0','5'],'athletes':[{'athlete':{'id':'2','displayName':'WR'},'stats':['3','49','0','5']}]}]}]}}
  rows,checks=extract(summary);self.assertEqual(rows[0]['stats']['receiving_yards'],49);self.assertEqual(len([c for c in checks if not c['matches']]),1);self.assertEqual(rows[0]['stats']['receiving_tds'],0)
if __name__=='__main__':unittest.main()
