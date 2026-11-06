import unittest
from scripts.refresh_team_research import summarize_stats
class TeamResearchTests(unittest.TestCase):
 def test_rates_use_aggregate_denominators_and_preserve_missing_values(self):
  out=summarize_stats([{'completions':1,'attempts':2,'rushing_yards':0,'carries':0},{'completions':9,'attempts':10}]);self.assertAlmostEqual(out['rates']['completion_percentage'],100*10/12);self.assertEqual(out['totals']['rushing_yards'],0);self.assertEqual(out['coverageByStat']['rushing_yards'],1);self.assertIsNone(out['totals']['passing_epa']);self.assertIsNone(out['rates']['rushing_yards_per_carry'])
