import unittest
import pandas as pd
from scripts.refresh_team_research import summarize_stats,current_team_catalog
class TeamResearchTests(unittest.TestCase):
 def test_rates_use_aggregate_denominators_and_preserve_missing_values(self):
  out=summarize_stats([{'completions':1,'attempts':2,'rushing_yards':0,'carries':0},{'completions':9,'attempts':10}]);self.assertAlmostEqual(out['rates']['completion_percentage'],100*10/12);self.assertEqual(out['totals']['rushing_yards'],0);self.assertEqual(out['coverageByStat']['rushing_yards'],1);self.assertIsNone(out['totals']['passing_epa']);self.assertIsNone(out['rates']['rushing_yards_per_carry'])

 def test_current_franchises_override_legacy_catalog_aliases(self):
  catalog=pd.DataFrame([{'team_abbr':'LAC','team_name':'Los Angeles Chargers'},{'team_abbr':'SD','team_name':'San Diego Chargers'},{'team_abbr':'LA','team_name':'Los Angeles Rams'},{'team_abbr':'STL','team_name':'St. Louis Rams'},{'team_abbr':'LV','team_name':'Las Vegas Raiders'},{'team_abbr':'OAK','team_name':'Oakland Raiders'}]);current=current_team_catalog(catalog);self.assertEqual(current['LAC']['team_name'],'Los Angeles Chargers');self.assertEqual(current['LAR']['team_name'],'Los Angeles Rams');self.assertEqual(current['LV']['team_name'],'Las Vegas Raiders')
