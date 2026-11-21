import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pandas as pd
from edge.routes import scenario

class RouteScenarioTests(unittest.TestCase):
 def evaluate(self,shares,route_changes=None):
  player=SimpleNamespace(player_id='p',player_display_name='Player',team='SEA')
  history=pd.DataFrame([dict(player_id='p',season=2026,forecast=False,targets=5,receptions=3,receiving_yards=40,offense_pct=share,receiving_air_yards=40,receiving_yards_after_catch=10) for share in shares])
  route={'Routes Run':len(shares)*20,'Targets/Route Run':.25,'Receptions':len(shares)*3,'Rec. Yards':len(shares)*40,'ADoT':8.,'YAC':len(shares)*10,**(route_changes or {})}
  with patch('edge.routes.match_snapshot',return_value=(route,{'source':'public','asOf':'2026-11-20T00:00Z'})):
   return scenario(player,history,{},2026,pd.Timestamp('2026-11-21',tz='UTC'))
 def test_recent_missing_snaps_do_not_crash_entire_weekly_model(self):
  for shares in [[.8,.8,np.nan,np.nan,np.nan],[np.nan]*4,[np.inf]*4,[0.]*4]:
   with self.subTest(shares=shares):self.assertEqual(self.evaluate(shares)['status'],'unavailable')
 def test_valid_route_scenario_remains_finite_and_reproducible(self):
  result=self.evaluate([.7,.8,.8,.9]);self.assertEqual(result['status'],'research_scenario');self.assertEqual(len(result['samples']),512);self.assertTrue(np.isfinite(result['samples']).all());self.assertEqual(result,self.evaluate([.7,.8,.8,.9]))
 def test_nonfinite_public_route_values_are_unavailable(self):
  for key in ['Routes Run','Targets/Route Run','ADoT','YAC']:
   with self.subTest(key=key):self.assertEqual(self.evaluate([.8]*4,{key:np.nan})['status'],'unavailable')
